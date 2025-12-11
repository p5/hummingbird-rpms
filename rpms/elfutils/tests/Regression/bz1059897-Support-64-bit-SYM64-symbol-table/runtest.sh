#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/bz1059897-Support-64-bit-SYM64-symbol-table
#   Description: Test for BZ#1059897 (Support 64-bit /SYM64/ symbol table)
#   Author: Vaclav Kadlcik <vkadlcik@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2014 Red Hat, Inc.
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation, either version 2 of
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

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="elfutils"

TEST_ARCHIVE_1='libantlr.a' # see PURPOSE & Bugzilla

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "cp ${TEST_ARCHIVE_1}.bz2 $TmpDir" 0 "Copying test files"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest

        rlRun "bunzip2 ${TEST_ARCHIVE_1}.bz2"
        rlAssertExists "$TEST_ARCHIVE_1"

        rlRun -s "eu-ar t $TEST_ARCHIVE_1" 0 "Checking eu-ar runs"
        rlAssertExists "$rlRun_LOG"
        rlAssertGrep '^/SYM64/$' "$rlRun_LOG"
        rlAssertGrep '^ANTLRUtil\.o$' "$rlRun_LOG"

        rlRun -s "eu-readelf -a $TEST_ARCHIVE_1" 0 "Checking eu-readelf runs"
        rlAssertExists "$rlRun_LOG"
        rlAssertGrep '^ELF Header:$' "$rlRun_LOG"

    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
