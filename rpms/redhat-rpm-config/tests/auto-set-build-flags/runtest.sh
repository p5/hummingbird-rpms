#!/bin/bash

set -ex

dnf -y builddep test.spec
rpmbuild --define "_sourcedir $PWD" -bi test.spec
rpmbuild --without auto_set_build_flags --define "_sourcedir $PWD" -bi test.spec
