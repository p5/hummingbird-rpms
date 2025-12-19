#!/bin/bash

set -ex

lib_dir=brp-llvm-compile-lto-elf-test-lib
lib_spec=$lib_dir/brp-llvm-compile-lto-elf-test-lib.spec

dnf -y builddep $lib_spec 
rpmbuild --define "_sourcedir $PWD/$lib_dir" --define "_rpmdir $PWD"  -bb $lib_spec

dnf -y install ./`rpm --eval '%{_arch}'`/*.rpm

test_dir=brp-llvm-compile-lto-elf-test
test_spec=$test_dir/brp-llvm-compile-lto-elf-test.spec

dnf -y builddep $test_spec
rpmbuild --define "_sourcedir $PWD/$test_dir" -bi $test_spec
