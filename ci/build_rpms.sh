#! /bin/bash -e

# Build RPMs for a given package using mock in a containerized environment.
#
# This script:
# - Builds the RPM using mock in the upstream RPM Build Pipeline container
# - Outputs binary RPMs to builds/PACKAGE_NAME/RPMS/
# - Outputs source RPMs to builds/PACKAGE_NAME/SRPMS/
#
# Usage: ./ci/build_rpms.sh [OPTIONS] PACKAGE_NAME
#   PACKAGE_NAME - Name of the package directory in rpms/
#   --arch ARCH  - Target architecture (default: $(uname -m))
#
# The built RPMs can be found in: builds/PACKAGE_NAME/RPMS/ and builds/PACKAGE_NAME/SRPMS/
#
# Note: This performs a non-hermetic package build in the same container
# environment as used by Konflux, but is not a drop-in replacement for the
# full Tekton pipeline.
#
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RPM_DIR=${SCRIPT_DIR}/../rpms
OUT_DIR=${SCRIPT_DIR}/../builds
REPO_ROOT=${SCRIPT_DIR}/..

image=quay.io/redhat-user-workloads/rpm-build-pipeline-tenant/environment:latest@sha256:56bde7a1040650bc14ee927534426a52d88de30d588048c6a08be7a8758372cb
arch=$(uname -m)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)
            arch="$2"
            shift 2
            ;;
        *)
            package_name="$1"
            shift
            ;;
    esac
done

test -n "${package_name}" || exit 1

# Use builds directory as workdir for easier debugging
workdir="${OUT_DIR}/${package_name}"
mkdir -p "${workdir}"

cd "${workdir}"
mkdir -p results
mkdir -p config
mkdir -p sources

# Create directory for mock buildroot on host filesystem (avoids overlayfs xattr issues)
mkdir -p var_lib_mock

# Allow mockbuilder (group mock) to read config and write results
podman unshare setfacl -m g:135:rwx -m default:g:135:rwx "results"
podman unshare setfacl -m g:135:rwx -m default:g:135:rwx "config"
podman unshare setfacl -m g:135:rwx -m default:g:135:rwx "sources"
podman unshare chgrp 135 "var_lib_mock"
podman unshare chmod g+rwx "var_lib_mock"

# Copy local source files to sources directory
cp -f "${RPM_DIR}/${package_name}"/* "${workdir}/sources/" 2>/dev/null || true

# prepare mock config
sed "s|@ARCH@|${arch}|" "${SCRIPT_DIR}/../mock/mock.cfg" > "${workdir}/config/mock.cfg"

# Detect git directory location (handle worktrees)
if [[ -f "${REPO_ROOT}/.git" ]]; then
    # Git worktree - read the gitdir location (may be relative)
    gitdir=$(grep 'gitdir:' "${REPO_ROOT}/.git" | cut -d' ' -f2) || true
    gitdir="${gitdir:-}"
    # Strip /worktrees/* to get the bare repo root
    bare_repo_relative="${gitdir%/worktrees/*}"
    # Convert to absolute path (resolve relative to REPO_ROOT)
    bare_repo=$(cd "${REPO_ROOT}" && realpath "${bare_repo_relative}")
else
    # Regular git repo
    bare_repo="${REPO_ROOT}/.git"
fi

podman run --rm -ti --privileged --init \
    --pids-limit=16384 \
    -u mockbuilder \
    -v "${workdir}/results:/results:z" \
    -v "${workdir}/config:/config:z" \
    -v "${workdir}/sources:/sources:z" \
    -v "${workdir}/var_lib_mock:/var/lib/mock:z" \
    -v "${REPO_ROOT}:/repo:z" \
    -v "${bare_repo}:/bare:z" \
    -e "CURL_HOME=/tmp" \
    "${image}" \
bash -euo pipefail -c "
# Configure curl's header until https://github.com/release-engineering/dist-git/issues/88 is fixed
echo 'header = \"Accept-Encoding: identity\"' > /tmp/.curlrc

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

# Organize RPMs into separate directories
mkdir -p "${workdir}/RPMS" "${workdir}/SRPMS"
mv -f "${workdir}"/results/*.src.rpm "${workdir}/SRPMS/" 2>/dev/null || true
mv -f "${workdir}"/results/*.rpm "${workdir}/RPMS/" 2>/dev/null || true

echo ""
echo "Binary RPMs:"
ls "${workdir}/RPMS"/*.rpm 2>/dev/null || echo "No binary RPMs found"

echo ""
echo "Source RPMs:"
ls "${workdir}/SRPMS"/*.src.rpm 2>/dev/null || echo "No source RPMs found"

echo ""
echo "Build outputs saved to: ${workdir}/"
