#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-token-sanity-test
#   Description: Test basic ip token funcionality
#
#   Author: Susant Sahani <susant@redhat.com>
#   Copyright (c) 2018 Red Hat, Inc.
#~~~

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="iproute"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "cp ip-token-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip token tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-token-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-token-tests.py"
        rlLog "ip token tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
