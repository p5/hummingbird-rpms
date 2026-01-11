#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/babeltrace/Regression/testsuite
#   Description: testsuite
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2019 Red Hat, Inc.
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

export PACKAGE="babeltrace"

rlJournalStart
    rlPhaseStartSetup
	# babeltrace itself comes from the rhel8 buildroot repo
        rlAssertRpm $PACKAGE
        rlRun "TMP=\$(mktemp -d)"
        rlRun "pushd $TMP"

	rlFetchSrcForInstalled $PACKAGE
	rlRun "dnf --nobest builddep -y *src.rpm"
	rlRun "rpm --define='_topdir $TMP' -Uvh *src.rpm"
	rlRun "rpmbuild --define='_topdir $TMP' -bc SPECS/${PACKAGE}.spec"
	rlRun "pushd BUILD/${PACKAGE}-*-build/${PACKAGE}-*"
    rlPhaseEnd

    rlPhaseStartTest
        set -o pipefail
	rlRun "make check |& tee test.log"
	rlFileSubmit test.log
    rlPhaseEnd

    rlPhaseStart FAIL "Double check the test result"
    # I didn't see the testsute failing and so I'm not sure if
    # make check would return non-zero exitcode in case of failure.
    # It almost certainly would.  But let's additionally parse
    # the log to make sure we'd catch a failure.
    rlRun "grep '^PASS:\ ' test.log"
    rlRun "grep '^FAIL:\ ' test.log" 1
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "popd"
        rlRun "rm -r $TMP"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
