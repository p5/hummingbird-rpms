#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-address-label-sanity-test
#   Description: Test basic ip address label funcionality
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
        rlRun "cp ip-address-label-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip address label tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-address-label-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-address-label-tests.py"
        rlLog "ip address label tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
