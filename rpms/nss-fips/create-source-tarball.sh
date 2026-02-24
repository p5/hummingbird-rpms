#!/usr/bin/bash
#
# Create the nss-fips source tarball
#
# This script downloads the RHEL 9.2 NSS RPMs from Red Hat CDN
# using UBI9 containers with subscription-manager authentication,
# then packages them into a tar.gz source tarball.
#
# For aarch64 packages, it uses QEMU emulation via podman.
#
# Usage: ./create-source-tarball.sh --org <ORG_ID> --key <ACTIVATION_KEY>
#
#   --org, -o   Red Hat subscription organization ID
#   --key, -k   Red Hat subscription activation key
#
# Alternatively, set environment variables:
#   RHSM_ORG_ID        - Organization ID
#   RHSM_ACTIVATION_KEY - Activation key
#
# Requirements:
# - podman
# - qemu-user-static (for aarch64 emulation)
# - Internet access to Red Hat CDN
#
set -euo pipefail

# Parse command-line arguments
ORG_ID="${RHSM_ORG_ID:-}"
ACTIVATION_KEY="${RHSM_ACTIVATION_KEY:-}"

usage() {
    echo "Usage: $0 --org <ORG_ID> --key <ACTIVATION_KEY>"
    echo ""
    echo "Options:"
    echo "  --org, -o    Red Hat subscription organization ID"
    echo "  --key, -k    Red Hat subscription activation key"
    echo ""
    echo "Environment variables (alternative to CLI args):"
    echo "  RHSM_ORG_ID         - Organization ID"
    echo "  RHSM_ACTIVATION_KEY - Activation key"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --org|-o)
            ORG_ID="$2"
            shift 2
            ;;
        --key|-k)
            ACTIVATION_KEY="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [[ -z "${ORG_ID}" ]]; then
    echo "ERROR: Organization ID is required (--org or RHSM_ORG_ID)"
    usage
fi

if [[ -z "${ACTIVATION_KEY}" ]]; then
    echo "ERROR: Activation key is required (--key or RHSM_ACTIVATION_KEY)"
    usage
fi

# NSS version from RHEL 9.2 with FIPS certification
VERSION="3.90.0"
RELEASE="6.el9_2"
OVR="${VERSION}-${RELEASE}"
TARBALL_NAME="nss-fips-${VERSION}"

# Architectures to download
ARCHES=(x86_64 aarch64)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/${TARBALL_NAME}"

echo "=== Creating nss-fips source tarball ==="
echo "Version: ${VERSION}"
echo "RHEL Release: ${RELEASE}"
echo "Architectures: ${ARCHES[*]}"
echo ""

# Clean up any previous work
rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"

# Function to download RPMs for a specific architecture
download_rpms_for_arch() {
    local arch=$1
    local platform

    echo ""
    echo "=== Downloading RPMs for ${arch} ==="

    # Map arch to container platform
    case "${arch}" in
        x86_64)
            platform="linux/amd64"
            ;;
        aarch64)
            platform="linux/arm64"
            ;;
        *)
            echo "Unsupported architecture: ${arch}"
            exit 1
            ;;
    esac

    # Create the download script for this architecture
    # Note: ACTIVATION_KEY and ORG_ID are passed as environment variables to the container
    cat > "${WORK_DIR}/download-${arch}.sh" << 'INNER_EOF'
#!/bin/bash
set -euo pipefail

# These are passed as environment variables from the host
if [[ -z "${ACTIVATION_KEY:-}" ]] || [[ -z "${ORG_ID:-}" ]]; then
    echo "ERROR: ACTIVATION_KEY and ORG_ID must be set as environment variables"
    exit 1
fi

echo "Registering with subscription-manager..."
subscription-manager register --activationkey="${ACTIVATION_KEY}" --org="${ORG_ID}"

echo "Enabling required repositories (EUS for RHEL 9.2)..."
subscription-manager repos --enable=rhel-9-for-${ARCH}-baseos-eus-rpms
subscription-manager repos --enable=rhel-9-for-${ARCH}-baseos-eus-debug-rpms
subscription-manager repos --enable=rhel-9-for-${ARCH}-baseos-eus-source-rpms
subscription-manager repos --enable=rhel-9-for-${ARCH}-appstream-eus-rpms

# Set release version to 9.2 to ensure we get the correct packages
subscription-manager release --set=9.2

echo "Refreshing repository metadata..."
dnf clean all
dnf makecache

cd /output

echo "=== Downloading binary RPMs for ${ARCH} ==="
# Only download softokn and freebl - these are the FIPS-validated modules
dnf download nss-softokn-${OVR}
dnf download nss-softokn-freebl-${OVR}

echo ""
echo "=== Downloaded files ==="
ls -la /output/*.rpm

echo ""
echo "Unregistering..."
subscription-manager unregister || true

echo "Done downloading RPMs for ${ARCH}"
INNER_EOF

    chmod +x "${WORK_DIR}/download-${arch}.sh"

    echo "Running ${platform} container for ${arch}..."
    podman run --rm \
        --platform "${platform}" \
        -v "${WORK_DIR}:/output:Z" \
        -e "ACTIVATION_KEY=${ACTIVATION_KEY}" \
        -e "ORG_ID=${ORG_ID}" \
        -e "ARCH=${arch}" \
        -e "OVR=${OVR}" \
        registry.access.redhat.com/ubi9/ubi:latest \
        /bin/bash /output/download-${arch}.sh

    # Clean up download script
    rm -f "${WORK_DIR}/download-${arch}.sh"
}

# Download RPMs for each architecture
for arch in "${ARCHES[@]}"; do
    download_rpms_for_arch "${arch}"
done

echo ""
echo "=== Verifying downloaded files ==="
echo "Contents of ${WORK_DIR}:"
ls -la "${WORK_DIR}/"

# Verify required files exist
echo ""
echo "=== Checking required files ==="
REQUIRED_FILES=()
for arch in "${ARCHES[@]}"; do
    REQUIRED_FILES+=(
        "nss-softokn-${OVR}.${arch}.rpm"
        "nss-softokn-freebl-${OVR}.${arch}.rpm"
    )
done

MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "${WORK_DIR}/${file}" ]; then
        echo "OK ${file}"
    else
        echo "MISSING ${file} (REQUIRED)"
        MISSING=1
    fi
done

if [ "${MISSING}" -eq 1 ]; then
    echo ""
    echo "ERROR: Some required files are missing!"
    exit 1
fi

# Create tarball - files should be at root level (no subdirectory)
echo ""
echo "=== Creating tarball ==="
cd "${WORK_DIR}"
tar -czvf "${SCRIPT_DIR}/${TARBALL_NAME}.tar.gz" *.rpm
cd "${SCRIPT_DIR}"

echo ""
echo "=== Tarball created ==="
ls -la "${TARBALL_NAME}.tar.gz"

# Generate SHA512 checksum
echo ""
echo "=== Generating SHA512 checksum ==="
CHECKSUM=$(sha512sum "${TARBALL_NAME}.tar.gz" | awk '{print $1}')
echo "SHA512 (${TARBALL_NAME}.tar.gz) = ${CHECKSUM}"

# Update sources file
echo "SHA512 (${TARBALL_NAME}.tar.gz) = ${CHECKSUM}" > sources
echo ""
echo "=== Updated sources file ==="
cat sources

# Clean up work directory
rm -rf "${WORK_DIR}"

echo ""
echo "=== Done ==="
echo "Tarball: ${SCRIPT_DIR}/${TARBALL_NAME}.tar.gz"
echo "Sources file updated with checksum"
