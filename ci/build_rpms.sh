#! /bin/bash -e

# Build RPMs for a given package using mock in a containerized environment.
#
# This script:
# - Builds the RPM using mock in the upstream RPM Build Pipeline container
# - Outputs both binary and source RPMs to a temporary results directory
#
# Usage: ./ci/build_rpms.sh [OPTIONS] PACKAGE_NAME
#   PACKAGE_NAME - Name of the package directory in rpms/
#
# The built RPMs can be found in: /tmp/konflux-build-PACKAGE_NAME-*/results/
#
# Note: This performs a non-hermetic package build in the same container
# environment as used by Konflux, but is not a drop-in replacement for the
# full Tekton pipeline.
#
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RPM_DIR=${SCRIPT_DIR}/../rpms
REPO_ROOT=${SCRIPT_DIR}/..

image=quay.io/redhat-user-workloads/rpm-build-pipeline-tenant/environment:latest@sha256:56bde7a1040650bc14ee927534426a52d88de30d588048c6a08be7a8758372cb
arch=x86_64

package_name=$1
test -n "${package_name}" || exit 1

workdir=$(mktemp -d "/tmp/konflux-build-${package_name}-XXXXXXXX")

cd "${workdir}"
mkdir results
mkdir config

# Allow mockbuilder (group mock) to read config and write results
podman unshare setfacl -m g:135:rwx -m default:g:135:rwx "results"
podman unshare setfacl -m g:135:rwx -m default:g:135:rwx "config"

# Copy local source files to sources directory
cp -f "${RPM_DIR}/${package_name}"/* "${workdir}/sources/" 2>/dev/null || true

# prepare mock config
sed "s|@ARCH@|${arch}|" "${SCRIPT_DIR}/../mock/mock.cfg" > "${workdir}/config/mock.cfg"

# Detect git directory location (handle worktrees)
if [[ -f "${REPO_ROOT}/.git" ]]; then
    # Git worktree - read the gitdir location
    gitdir=$(grep 'gitdir:' "${REPO_ROOT}/.git" | cut -d' ' -f2) || true
    gitdir="${gitdir:-}"
    bare_repo="${gitdir%/worktrees/*}"
else
    # Regular git repo
    bare_repo="${REPO_ROOT}/.git"
fi

podman run --rm -ti --privileged --init \
    --pids-limit=16384 \
    -u mockbuilder \
    -v "${workdir}/results:/results:z" \
    -v "${workdir}/config:/config:z" \
    -v "${RPM_DIR}/${package_name}:/sources:z" \
    -v "${REPO_ROOT}:/repo:z" \
    -v "${bare_repo}:/bare:z" \
    "${image}" \
bash -euo pipefail -c "
# Download sources using dist-git-client
# Copy package to writable location and set up .git for dist-git-client
cp -r /repo/rpms/${package_name} /tmp/package
pushd /tmp/package

# dist-git-client needs a .git directory even with --forked-from (it runs git commands)
cp -r /bare .git

echo 'Downloading sources via dist-git-client...'
# Use --forked-from to tell dist-git-client to use Fedora's lookaside cache
dist-git-client --forked-from https://src.fedoraproject.org/rpms/${package_name}.git sources

# Copy all downloaded sources to /sources directory
echo 'Copying sources to /sources directory...'
cp -v * /sources/ 2>/dev/null || true

mock -r /config/mock.cfg \
     --spec '/repo/rpms/${package_name}/${package_name}.spec' \
     --sources /sources \
     --resultdir /results

popd
"

echo "RPMs:"
ls "${workdir}"/results/*.rpm
