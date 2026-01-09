#!/bin/bash

set -ex

dnf -y build-dep test.spec
rpmbuild --define '_sourcedir .' --define '_builddir .' -bb test.spec
dnf -y build-dep test.spec -D "_with_ld_lld 1"
rpmbuild --with ld_lld --define '_sourcedir .' --define '_builddir .' -bb test.spec
dnf -y build-dep test.spec -D "_with_clang 1"
rpmbuild --with clang --define '_sourcedir .' --define '_builddir .' -bb test.spec
