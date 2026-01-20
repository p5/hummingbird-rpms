# BIND 9

[BIND (Berkeley Internet Name Domain)](https://www.isc.org/downloads/bind/doc/) is a complete, highly portable
implementation of the DNS (Domain Name System) protocol.

Internet Systems Consortium
([https://www.isc.org](https://www.isc.org)), a 501(c)(3) public benefit
corporation dedicated to providing software and services in support of the
Internet infrastructure, developed BIND 9 and is responsible for its
ongoing maintenance and improvement.

More details about upstream project can be found on their
[gitlab](https://gitlab.isc.org/isc-projects/bind9). This repository contains
only upstream sources and packaging instructions for
[Fedora Project](https://fedoraproject.org).

Any rebase requires to be built together with
[bind-dyndb-ldap](https://src.fedoraproject.org/rpms/bind-dyndb-ldap/) to prevent conflict
at installation of [freeipa-server-dns](https://src.fedoraproject.org/rpms/freeipa).
Stable bodhi updates are checked, but rawhide are not checked explicitly.
Symbol of libraries in *bind-libs* changes with every minor version change of bind,
therefore they break any package dependent on bind-libs.

## Subpackages

The package contains several subpackages, some of them can be disabled on rebuild.

* **bind** -- *named* daemon providing DNS server
* **bind-utils** -- set of tools to analyse DNS responses or update entries (dig, host)
* **bind-doc** -- documentation for current bind, *BIND 9 Administrator Reference Manual*.
* **bind-libs** -- Shared libraries used by some others programs
* **bind-devel** -- Development headers for libs. Can be disabled by `--without DEVEL`


## Optional features

* *GSSTSIG* -- Support for Kerberos authentication in BIND.
* *LMDB* -- Support for dynamic database for managing runtime added zones. Provides faster removal of added zone with much less overhead. But requires lmdb linked to base libs.
