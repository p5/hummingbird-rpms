#!/bin/bash
# SPDX-Licenetnse-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-netns-sanity-test
#   Description: Test basic ip netns funcionality
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
        rlRun "cp ip-netns-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip netns tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-netns-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-netns-tests.py"
        rlLog "ip netns tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
