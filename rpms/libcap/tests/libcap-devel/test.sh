#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1


rlJournalStart
    rlPhaseStartSetup
        rlRun "gcc -lcap -lcmocka -Wall -g3 -o test-libcap test-libcap.c"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "./test-libcap"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm test-libcap"
    rlPhaseEnd
rlJournalEnd
