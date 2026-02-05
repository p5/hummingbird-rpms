#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/m4/Regression/testsuite
#   Description: testsuite
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2015 Red Hat, Inc.
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

PACKAGE="m4"
VERSION=$(rpm -q m4 --qf '%{VERSION}')

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TMPD=$(mktemp -d)"
        rlRun "pushd $TMPD"
        rlFetchSrcForInstalled $PACKAGE
        rlRun "rpm --define='_topdir $TMPD' -Uvh m4-*src.rpm"
    rlPhaseEnd

    rlPhaseStart FAIL "Build the source"
        rlRun "rpmbuild --define='_topdir $TMPD' -bc SPECS/m4.spec > stdout.log 2> stderr.log"
        rlRun "test -f stderr.log && cat stderr.log || true"
        rlFileSubmit stdout.log
        rlFileSubmit stderr.log
    rlPhaseEnd

    rlPhaseStart FAIL "Run tests"
        rlRun "pushd $TMPD/BUILD/m4-${VERSION}-build/m4-${VERSION}"
        rlRun "eval `rpm --eval %___build_pre_env`"
        # el7 package creates couple tests/*log files (per testcase)
        # el6 package doesn't, so we'll create some explicitly
        rlRun "make check > tests/testout.log 2> tests/testerr.log"
        rlFileSubmit testout.log
        rlFileSubmit testerr.log
    rlPhaseEnd

    rlPhaseStart FAIL "Check for at least one PASSed test"
        rlRun "[[ $(grep ^PASS tests/*log | wc -l) -ge 1 ]]"
    rlPhaseEnd

    rlPhaseStart FAIL "Check for no FAILed test"
        rlRun "[[ $(cat tests/*log | grep FAIL | grep -P -v '^#' | wc -l) -eq 0 ]]"
    rlPhaseEnd

    rlPhaseStart FAIL "Show test results summary"
        test -f tests/test-suite.log && \
            rlRun "cat tests/test-suite.log" || \
            rlLogInfo "No summary available."
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd -2"
        rlRun "rm -r $TMPD"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
