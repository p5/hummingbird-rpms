#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-link-sanity-test
#   Description: Test basic ip link funcionality
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
        rlRun "cp ip-link-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip link tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-link-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-link-tests.py"
        rlLog "ip link tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
