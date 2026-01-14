#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-route-sanity-test
#   Description: Test basic ip route funcionality
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
        rlRun "cp ip-route-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip route tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-route-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-route-tests.py"
        rlLog "ip route tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
