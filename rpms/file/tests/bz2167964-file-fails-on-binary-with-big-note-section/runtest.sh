#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGES="file binutils"
rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm --all
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd \$tmp"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "truncate --size=100M note" 0 "Create a dummy 100 MB file"
        rlRun "objcopy --update-section .note.package=note /usr/bin/cp repro" \
            0 "Create a copy of cp with large .note.package section"
        rlRun "file repro" 0 "Run file of the reproducer"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r \$tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
