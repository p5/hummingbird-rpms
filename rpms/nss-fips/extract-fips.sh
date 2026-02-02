#!/usr/bin/bash -e
#
# Extract FIPS-validated NSS softokn and freebl binaries from RHEL RPMs
#
# This script extracts the libraries from the RHEL 9.2 NSS packages
# that have been submitted to NIST for FIPS 140-3 validation.
#
# Environment variables (set by rpmbuild):
#   RPM_BUILD_ROOT - Install root directory
#   RPM_BUILD_DIR  - Build directory
#   RPM_ARCH       - Target architecture
#   RHEL_NSS_VERSION - NSS version (e.g., 3.90.0)
#   RHEL_NSS_RELEASE - RHEL release (e.g., 6.el9_2)

if [[ -z "${RPM_BUILD_ROOT}" ]]; then
    echo >&2 "ERROR: RPM_BUILD_ROOT is not set"
    exit 1
fi

if [[ -z "${RHEL_NSS_VERSION}" ]]; then
    echo >&2 "ERROR: RHEL_NSS_VERSION is not set"
    exit 1
fi

if [[ -z "${RHEL_NSS_RELEASE}" ]]; then
    echo >&2 "ERROR: RHEL_NSS_RELEASE is not set"
    exit 1
fi

# Determine the library directory based on architecture
# 64-bit systems use /usr/lib64, 32-bit use /usr/lib
case "${RPM_ARCH}" in
    x86_64|aarch64|ppc64le|s390x)
        LIBDIR="/usr/lib64"
        ;;
    i386|i686|armv7hl)
        LIBDIR="/usr/lib"
        ;;
    *)
        # Default to lib64 for unknown 64-bit architectures
        if [[ $(getconf LONG_BIT) == "64" ]]; then
            LIBDIR="/usr/lib64"
        else
            LIBDIR="/usr/lib"
        fi
        ;;
esac

# Determine package architecture (RHEL packages use specific names)
PKG_ARCH=${RPM_ARCH}
if [[ "${PKG_ARCH}" == "i386" ]]; then
    PKG_ARCH=i686
fi

OVR="${RHEL_NSS_VERSION}-${RHEL_NSS_RELEASE}"

echo "=== Extracting FIPS-validated NSS binaries ==="
echo "NSS Version: ${RHEL_NSS_VERSION}"
echo "RHEL Release: ${RHEL_NSS_RELEASE}"
echo "Architecture: ${PKG_ARCH}"
echo "Library directory: ${LIBDIR}"
echo ""

# Create directories
install -d "${RPM_BUILD_ROOT}${LIBDIR}"
install -d "${RPM_BUILD_ROOT}${LIBDIR}/nss"
install -d "${RPM_BUILD_ROOT}${LIBDIR}/nss/saved"
install -d "${RPM_BUILD_ROOT}${LIBDIR}/nss/unsupported-tools"

# Create extraction directory
EXTRACT_DIR="${RPM_BUILD_DIR}/rhel-extract"
rm -rf "${EXTRACT_DIR}"
mkdir -p "${EXTRACT_DIR}"

pushd "${EXTRACT_DIR}" > /dev/null

echo "=== Extracting nss-softokn RPM ==="
SOFTOKN_RPM="${RPM_BUILD_DIR}/nss-softokn-${OVR}.${PKG_ARCH}.rpm"
if [[ ! -f "${SOFTOKN_RPM}" ]]; then
    echo >&2 "ERROR: Cannot find ${SOFTOKN_RPM}"
    exit 1
fi
rpm2cpio "${SOFTOKN_RPM}" | cpio -idm --quiet

echo "=== Extracting nss-softokn-freebl RPM ==="
FREEBL_RPM="${RPM_BUILD_DIR}/nss-softokn-freebl-${OVR}.${PKG_ARCH}.rpm"
if [[ ! -f "${FREEBL_RPM}" ]]; then
    echo >&2 "ERROR: Cannot find ${FREEBL_RPM}"
    exit 1
fi
rpm2cpio "${FREEBL_RPM}" | cpio -idm --quiet

echo ""
echo "=== Installing softokn libraries ==="

# Install libsoftokn3.so and its checksum file
SOFTOKN_SO=$(find . -name "libsoftokn3.so" -type f | head -1)
if [[ -z "${SOFTOKN_SO}" ]]; then
    echo >&2 "ERROR: libsoftokn3.so not found in RPM"
    exit 1
fi
install -m 755 "${SOFTOKN_SO}" "${RPM_BUILD_ROOT}${LIBDIR}/libsoftokn3.so"
echo "  Installed: libsoftokn3.so"

SOFTOKN_CHK=$(find . -name "libsoftokn3.chk" -type f | head -1)
if [[ -n "${SOFTOKN_CHK}" ]]; then
    install -m 644 "${SOFTOKN_CHK}" "${RPM_BUILD_ROOT}${LIBDIR}/libsoftokn3.chk"
    echo "  Installed: libsoftokn3.chk"
else
    echo "  WARNING: libsoftokn3.chk not found"
fi

echo ""
echo "=== Installing freebl libraries ==="

# Install libfreebl3.so and its checksum file
FREEBL3_SO=$(find . -name "libfreebl3.so" -type f | head -1)
if [[ -z "${FREEBL3_SO}" ]]; then
    echo >&2 "ERROR: libfreebl3.so not found in RPM"
    exit 1
fi
install -m 755 "${FREEBL3_SO}" "${RPM_BUILD_ROOT}${LIBDIR}/libfreebl3.so"
echo "  Installed: libfreebl3.so"

FREEBL3_CHK=$(find . -name "libfreebl3.chk" -type f | head -1)
if [[ -n "${FREEBL3_CHK}" ]]; then
    install -m 644 "${FREEBL3_CHK}" "${RPM_BUILD_ROOT}${LIBDIR}/libfreebl3.chk"
    echo "  Installed: libfreebl3.chk"
else
    echo "  WARNING: libfreebl3.chk not found"
fi

# Install libfreeblpriv3.so and its checksum file
FREEBLPRIV_SO=$(find . -name "libfreeblpriv3.so" -type f | head -1)
if [[ -z "${FREEBLPRIV_SO}" ]]; then
    echo >&2 "ERROR: libfreeblpriv3.so not found in RPM"
    exit 1
fi
install -m 755 "${FREEBLPRIV_SO}" "${RPM_BUILD_ROOT}${LIBDIR}/libfreeblpriv3.so"
echo "  Installed: libfreeblpriv3.so"

FREEBLPRIV_CHK=$(find . -name "libfreeblpriv3.chk" -type f | head -1)
if [[ -n "${FREEBLPRIV_CHK}" ]]; then
    install -m 644 "${FREEBLPRIV_CHK}" "${RPM_BUILD_ROOT}${LIBDIR}/libfreeblpriv3.chk"
    echo "  Installed: libfreeblpriv3.chk"
else
    echo "  WARNING: libfreeblpriv3.chk not found"
fi

popd > /dev/null

echo ""
echo "=== Verifying installed files ==="
echo "Libraries in ${RPM_BUILD_ROOT}${LIBDIR}/:"
ls -la "${RPM_BUILD_ROOT}${LIBDIR}/"*.so "${RPM_BUILD_ROOT}${LIBDIR}/"*.chk 2>/dev/null || true

echo ""
echo "=== Verifying checksums ==="
for lib in libsoftokn3.so libfreebl3.so libfreeblpriv3.so; do
    if [[ -f "${RPM_BUILD_ROOT}${LIBDIR}/${lib}" ]]; then
        sha256=$(sha256sum "${RPM_BUILD_ROOT}${LIBDIR}/${lib}" | awk '{print $1}')
        echo "  ${lib}: ${sha256:0:16}..."
    fi
done

# Cleanup
rm -rf "${EXTRACT_DIR}"

echo ""
echo "=== FIPS binary extraction complete ==="
