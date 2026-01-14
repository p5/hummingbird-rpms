#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-tuntap-sanity-test
#   Description: Test basic ip tuntap funcionality
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
        rlRun "cp ip-tuntap-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip tuntap tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-tuntap-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-tuntap-tests.py"
        rlLog "ip tuntap tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
