#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-l2tp-sanity-test
#   Description: Test basic ip l2tp funcionality
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
        rlRun "cp ip-l2tp-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip l2tp tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-l2tp-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-l2tp-tests.py"
        rlLog "ip l2tp tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
