# PyCA cryptography

https://cryptography.io/en/latest/

## Packaging python-cryptography

The example assumes

* Fedora Rawhide (f34)
* PyCA cryptography release ``3.4``
* Update Bugzilla issue is ``RHBZ#00000001``

### Build new python-cryptography

Switch and update branch

```shell
fedpkg switch-branch rawhide
fedpkg pull
```

Bump version and get sources

```shell
rpmdev-bumpspec -c "Update to 3.4 (#00000001)" -n 3.4 python-cryptography.spec
spectool -gf python-cryptography.spec
```

Upload new source

```shell
fedpkg new-sources cryptography-3.4.tar.gz
```

Commit changes

```shell
fedpkg commit --clog
fedpkg push
```

Build

```shell
fedpkg build
```

## RHEL/CentOS builds

RHEL and CentOS use a different approach for Rust crates packaging than
Fedora. On Fedora Rust dependencies are packaged as RPMs, e.g.
``rust-pyo3+default-devel`` RPM. These packages don't exist on RHEL and
CentOS. Instead python-cryptography uses a tar ball with vendored crates.
The tar ball is created by a script:

```shell
./vendor_rust.py
rhpkg upload cryptography-3.4-vendor.tar.bz2
```
