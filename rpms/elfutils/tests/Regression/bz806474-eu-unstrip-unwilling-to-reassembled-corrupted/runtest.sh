#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/bz806474-eu-unstrip-unwilling-to-reassembled-corrupted
#   Description: Test for BZ#806474 (eu-unstrip unwilling to reassembled corrupted)
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

TEST_STRIPPED='ld' # see PURPOSE, BZ#806474, and 698005
TEST_DEBUGIFO='ld.debug' # ditto
TEST_MERGED='ld-debug'

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "cp ${TEST_STRIPPED}.bz2 ${TEST_DEBUGIFO}.bz2 $TmpDir" 0 "Copying test files"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest

        rlRun "bunzip2 ${TEST_STRIPPED}.bz2" 0
        rlRun "bunzip2 ${TEST_DEBUGIFO}.bz2" 0
        rlAssertExists "$TEST_STRIPPED"
        rlAssertExists "$TEST_DEBUGIFO"

        rlRun -t -s "eu-unstrip -o $TEST_MERGED $TEST_STRIPPED $TEST_DEBUGIFO" 1 'unstrip with corrupted debuginfo'
        rlAssertNotExists "$TEST_MERGED"
        rlAssertGrep '^STDERR:.*ELF header identification.*different, use --force' "$rlRun_LOG"

        rlRun -t -s "eu-unstrip --force -o $TEST_MERGED $TEST_STRIPPED $TEST_DEBUGIFO" 0 'Forced unstrip with corrupted debuginfo'
        rlAssertExists "$TEST_MERGED"
        rlAssertGrep '^STDERR:.*WARNING:.*ELF header identification.*different' "$rlRun_LOG"

        rlRun -t -s "file $TEST_MERGED" 0 'Detecting type of merged file'
        rlAssertGrep '^STDOUT:.*not stripped$' "$rlRun_LOG"

        rlRun -s "eu-objdump -s $TEST_MERGED" 0 'Running objdump on merged file'
        rlAssertGrep '^Contents of section .debug_info:' "$rlRun_LOG"
        rlAssertGrep '^Contents of section .debug_line:' "$rlRun_LOG"

    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
