# OpenSSL FIPS Provider for Hummingbird

This package provides a NIST-validated OpenSSL FIPS cryptographic module for
use with Hummingbird.

## Overview

The FIPS module (`fips.so`) included in this package is extracted from RHEL 9.2
OpenSSL packages and has been submitted to NIST for FIPS 140-3 certification.

**Important**: This package does NOT build the FIPS module from source. Instead,
it performs a full source build to verify buildability, then replaces the built
binaries with the certified ones from RHEL packages.

## Package Structure

- `openssl-fips-provider` - Meta package (documentation only)
- `openssl-fips-provider-so` - Contains the actual `fips.so` module
- `openssl-fips-provider-so-debuginfo` - Debug symbols
- `openssl-fips-provider-so-debugsource` - Debug sources

## Source Tarball Contents

The source tarball (`openssl-fips-provider-3.0.7.tar.gz`) must contain:

1. `openssl-3.0.7-18.el9_2.src.rpm` - RHEL source RPM
2. `openssl-libs-3.0.7-18.el9_2.<arch>.rpm` - Binary RPM with fips.so
3. `openssl-libs-debuginfo-3.0.7-18.el9_2.<arch>.rpm` - Debug info
4. `openssl-debuginfo-3.0.7-18.el9_2.<arch>.rpm` - Debug info
5. `openssl-debugsource-3.0.7-18.el9_2.<arch>.rpm` - Debug sources

Where `<arch>` is the target architecture (x86_64, aarch64, etc.).

## Building

```bash
# Build using mock
./ci/build_rpms.sh openssl-fips-provider
```

## Usage

Once installed, the FIPS provider will be available at:

```bash
/usr/lib64/ossl-modules/fips.so
```

To enable FIPS mode, configure OpenSSL to load the FIPS provider in your
`openssl.cnf` or application configuration.

## References

- [OpenSSL FIPS Documentation](https://www.openssl.org/docs/fips.html)
- [NIST CMVP](https://csrc.nist.gov/projects/cryptographic-module-validation-program)
