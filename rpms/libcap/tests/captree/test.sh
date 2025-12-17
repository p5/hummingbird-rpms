#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart

if rpm --eval '%{golang_arches}' | tr ' ' '\n' | grep -q -e "$(rpm --eval '%{_arch}')"; then
    rlPhaseStartTest "Should display help"
    rlRun "captree -h"
    rlPhaseEnd

    rlPhaseStartTest "Should list capabilities of pid 1"
    rlRun -s "captree --depth 1 1"
    rlAssertGrep 'systemd.*=ep' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should display sys admin capability"
    rlRun -s "capsh --drop=cap_sys_admin -- -c 'captree --verbose \$\$'"
    rlAssertGrep "!cap_sys_admin" $rlRun_LOG
    rlPhaseEnd
fi

rlJournalEnd
