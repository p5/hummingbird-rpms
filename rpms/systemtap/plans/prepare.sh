#!/bin/bash

# On Rawhide, the running kernel packages won't probably be avail in
# configured repos.  Debuginfo isn't a problem, we access that using
# the debuginfod.
__fedora_install_deps ()
{
    TMPD=$(mktemp -d)
    pushd $TMPD
    koji download-build --rpm kernel-`uname -r` --arch `uname -i`
    koji download-build --rpm kernel-devel-`uname -r` --arch `uname -i`
    koji download-build --rpm kernel-modules-`uname -r` --arch `uname -i`
    dnf -y install kernel{,-devel,-modules}-`uname -r`.rpm
    popd
    rm -rf $TMPD
}

set -xe

source /etc/os-release

# Install needed packages
if [ "$ID" == "fedora" ]; then
    stap-prep || __fedora_install_deps
fi
stap-prep

# Report installed packages
stap-report

# Set up SELinux so that it allows for userspace probing
setsebool allow_execmod on
setsebool allow_execstack on
setsebool deny_ptrace off

set +xe
