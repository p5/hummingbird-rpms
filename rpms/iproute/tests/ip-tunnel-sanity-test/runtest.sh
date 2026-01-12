#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-tunnel-sanity-test
#   Description: Test basic ip tunnel funcionality
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
        rlRun "cp ip-tunnel-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip tunnel tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-tunnel-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-tunnel-tests.py"
        rlLog "ip tunnel tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
