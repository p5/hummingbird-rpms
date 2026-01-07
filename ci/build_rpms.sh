#! /bin/bash -e

# Build RPMs for a given package using mock in a containerized environment.
#
# This script:
# - Builds the RPM using mock in the upstream RPM Build Pipeline container
# - Outputs binary RPMs to builds/PACKAGE_NAME/RPMS/
# - Outputs source RPMs to builds/PACKAGE_NAME/SRPMS/
#
# Usage: ./ci/build_rpms.sh [OPTIONS] PACKAGE_NAME
#   PACKAGE_NAME       - Name of the package directory in rpms/
#   --arch ARCH        - Target architecture (default: $(uname -m))
#   --build-dir DIR    - Custom build directory (default: builds/PACKAGE_NAME)
#   --local-rpms-dir DIR - Directory containing local RPMs to use as an additional
#                        high-priority repo (useful for testing build compatibility)
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
build_dir=""
local_rpms_dir=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --arch)
            arch="$2"
            shift 2
            ;;
        --build-dir)
            build_dir="$2"
            shift 2
            ;;
        --local-rpms-dir)
            local_rpms_dir="$(realpath "$2")"
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
if [[ -n "${build_dir}" ]]; then
    workdir="${build_dir}"
else
    workdir="${OUT_DIR}/${package_name}"
fi
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

# If local RPMs are specified, add a high-priority local repo to the mock config
if [[ -n "${local_rpms_dir}" ]]; then
    # Verify the directory exists and contains RPMs
    if [[ ! -d "${local_rpms_dir}" ]]; then
        echo "Error: Local RPMs directory does not exist: ${local_rpms_dir}" >&2
        exit 1
    fi
    if ! ls "${local_rpms_dir}"/*.rpm &>/dev/null; then
        echo "Warning: No RPM files found in ${local_rpms_dir}" >&2
    fi

    # Inject local repo config into mock.cfg at the anchor point
    # Priority 1 ensures it takes precedence over all other repos
    # Uses /tmp/local-rpms which is created inside the container from the mounted source
    local_repo_config=$(cat <<'EOF'
[local-rpms]
name=local-rpms
baseurl=file:///tmp/local-rpms/
enabled=1
gpgcheck=0
priority=1
EOF
)
    content=$(<"${workdir}/config/mock.cfg")
    printf '%s\n' "${content//# @LOCAL_RPMS_REPO@/${local_repo_config}}" > "${workdir}/config/mock.cfg"
    echo "Local RPMs repo configured from: ${local_rpms_dir}"
fi

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

# Build podman arguments
podman_args=(
    --rm -ti --privileged --init
    --pids-limit=16384
    -u mockbuilder
    -v "${workdir}/results:/results:z"
    -v "${workdir}/config:/config:z"
    -v "${workdir}/sources:/sources:z"
    -v "${workdir}/var_lib_mock:/var/lib/mock:z"
    -v "${REPO_ROOT}:/repo:z"
    -v "${bare_repo}:/bare:z"
    -e "CURL_HOME=/tmp"
)

# Add local RPMs mount if specified (read-only source, will be copied inside container)
if [[ -n "${local_rpms_dir}" ]]; then
    podman_args+=(-v "${local_rpms_dir}:/local-rpms-src:ro,z")
fi

podman run "${podman_args[@]}" "${image}" \
bash -euo pipefail -c "
# Configure curl's header until https://github.com/release-engineering/dist-git/issues/88 is fixed
echo 'header = \"Accept-Encoding: identity\"' > /tmp/.curlrc

# Create repo from local RPMs if mounted
if [[ -d /local-rpms-src ]]; then
    echo 'Creating repository from local RPMs...'
    mkdir -p /tmp/local-rpms
    cp /local-rpms-src/*.rpm /tmp/local-rpms/ 2>/dev/null || true
    createrepo_c /tmp/local-rpms
fi

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
