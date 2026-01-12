#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-fou-sanity-test
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
        rlRun "modprobe fou"
        rlRun "cp ip-fou-tests.py /usr/bin"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "ip fou tests"
        rlRun "/usr/bin/python3 /usr/bin/ip-fou-tests.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm /usr/bin/ip-fou-tests.py"
        rlLog "ip fou tests done"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd

rlGetTestState
