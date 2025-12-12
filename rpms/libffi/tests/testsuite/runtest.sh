#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/libffi/Sanity/testsuite
#   Description: Runs upstream testsuite
#   Author: Michal Nowak <mnowak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2010 Red Hat, Inc. All rights reserved.
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see http://www.gnu.org/licenses/.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include rhts environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGES=(libffi libffi-devel gcc dejagnu rpm-build gcc-c++)

rlJournalStart
    rlPhaseStartSetup
        for p in "${PACKAGES[@]}"; do
            if ! rlCheckRpm "$p"; then
                rlRun "yum -y install $p"
                rlAssertRpm "$p"
            fi
        done;

        rlRun "TmpDir=$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlFetchSrcForInstalled libffi
        rlRun "rpm -ivh libffi*.src.rpm"
        rlRun "popd"
        rlRun "specfile=$(rpm --eval='%_specdir')/libffi.spec"
        rlRun "rpmbuild -bp --undefine specpartsdir $specfile"
        rlRun "builddir=$(rpm --eval='%_builddir')"
        rlRun "pushd $(dirname "$(find $builddir -name configure)")"
        rlRun "./configure"
        rlRun "make"
    rlPhaseEnd

    rlPhaseStartTest "Run testsuite"
        set -xe
        # Patch the testsuite to run with the installed libffi libraries, not
        # with the ones built from the rpm.
        # Do not add the current dir or the build dir to ld_library_path
        sed -i 's/set ld_library_path "."/set ld_library_path ""/' testsuite/lib/libffi*.exp
        sed -i '/append ld_library_path.*blddirffi/d' testsuite/lib/libffi*.exp
        # Set ld_library_path to the system libdir (typically /usr/lib or /usr/lib64)
        MYLIBDIR=$(rpm --eval '%{_libdir}')
        sed -i 's;set libffi_dir.*"[^"]*";set libffi_dir "'"${MYLIBDIR}"'";' testsuite/lib/libffi*.exp
        grep -F -e 'set ld_library_path' -e 'set libffi_dir' testsuite/lib/libffi.exp
        # As of upstream commit 40a7682 the link flags hardcode the library dir so we need to edit that too
        # by removing the explicit library seach path to the built libraries.
        # https://github.com/libffi/libffi/commit/40a7682#diff-b4e449eb85934de2bdcf9ee0ac320872a7d09d60df6a24e3f066d7d74f6ddfd0R345
        sed -i 's;set libffi_link_flags "-L[^"]*";set libffi_link_flags "";' testsuite/lib/libffi*.exp
        set +xe
        rlLog "Checking whether we test really the installed libraries."
        strace -F -e open,openat,stat -o strace.log -- make check
        # Count library calls from places different than the libdir we want (MYLIBDIR)
        LIBFFI_SO_CALLS=$(cat strace.log | grep libffi.so | grep -v ENOENT | grep -v "/usr" | grep -v '"/lib' | grep -c -v 'unfinished')
        rlAssertGreater "The just built libraries should not be used, everything should be taken from /usr" 5 "$LIBFFI_SO_CALLS"
        rlRun "cat strace.log | grep libffi.so | grep /usr"
        rlRun "cat strace.log | grep libffi.so | grep rpmbuild" 1
        rlRun "make check" 0 "RUNNING THE TESTSUITE"
        rlRun "popd"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "ls -al $TmpDir"
        rlBundleLogs logs "$(find . -name 'libffi.sum')" "$(find . -name 'libffi.log')"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
