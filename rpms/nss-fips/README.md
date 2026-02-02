# NSS FIPS Modules for Hummingbird

This package provides NIST-validated NSS FIPS cryptographic modules for
use with Hummingbird.

## Overview

The FIPS modules (libsoftokn3.so, libfreebl3.so, libfreeblpriv3.so) included
in this package are extracted from RHEL 9.2 NSS packages that have been
submitted to NIST for FIPS 140-3 certification.

**Important**: This package does NOT build the FIPS modules from source.
Instead, it extracts the pre-built, validated binaries from RHEL packages
to ensure the exact checksums match those submitted to NIST.

## Package Structure

| Subpackage | Description | Conflicts with |
|------------|-------------|----------------|
| `nss-softokn-fips` | PKCS#11 software token module | `nss-softokn` |
| `nss-softokn-freebl-fips` | Low-level crypto primitives | `nss-softokn-freebl` |

**Why the naming?** Package names are chosen so that `nss-softokn-fips` comes
AFTER `nss-softokn` alphabetically. This ensures DNF prefers the standard
non-FIPS packages when both are available and no explicit choice is made.

## FIPS Module Details

- **Source**: RHEL 9.2 (nss-3.90.0-6.el9_2)
- **Validation Status**: Submitted to NIST for FIPS 140-3
- **Libraries**:
  - `libsoftokn3.so` - PKCS#11 software token
  - `libfreebl3.so` - Freebl cryptographic library
  - `libfreeblpriv3.so` - Private freebl interface

## How It Works

When installed, these packages:

1. **Conflict** with the standard `nss-softokn` and `nss-softokn-freebl` packages
2. **Provide** the `nss-softokn` capability to satisfy nss dependencies
3. **Include** the `.chk` files required for FIPS self-tests

The rest of NSS (libnss3.so, libssl3.so, etc.) continues to come from the
standard `nss` package.

## Version Considerations

The FIPS modules are older because NIST validation takes 12-24 months and
covers specific binary checksums. Rebuilding from source would invalidate
the certification.

## Source Tarball Contents

The source tarball (`nss-fips-3.90.0.tar.gz`) contains:

- `nss-softokn-3.90.0-6.el9_2.<arch>.rpm` - Binary RPM with libsoftokn3.so
- `nss-softokn-freebl-3.90.0-6.el9_2.<arch>.rpm` - Binary RPM with libfreebl*.so

## Recreating the Source Tarball

To recreate the source tarball (requires Red Hat subscription):

```bash
./create-source-tarball.sh --org <ORG_ID> --key <ACTIVATION_KEY>
```

This downloads the RHEL 9.2 packages from Red Hat CDN using a UBI9 container.

## Enabling FIPS Mode in Containers

For container environments, FIPS mode is typically inherited from the host
or enabled via environment variables:

```bash
# Check if FIPS mode is active
cat /proc/sys/crypto/fips_enabled
```

## References

- [NSS Documentation](https://firefox-source-docs.mozilla.org/security/nss/)
- [NIST CMVP](https://csrc.nist.gov/projects/cryptographic-module-validation-program)
- [RHEL 9 Security Hardening](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/security_hardening/)
