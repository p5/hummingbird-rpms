#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest "libcap pkg-config should be present and valid"
        rlRun "rpm -ql libcap-devel | grep libcap.pc" 0 "There must be libcap.pc"
        if [ $? -eq 0 ]; then
          PCFILE=$(rpm -ql libcap-devel | grep libcap.pc)
          rlRun "pkg-config --libs libcap | grep -- '-lcap'"
          VER=$(awk '/Version:/ { print $2 }' $PCFILE | tail -1)
          rlRun "pkg-config --modversion libcap | grep $VER"
          rlRun -s "pkg-config --print-variables libcap"
          rlAssertGrep "^prefix" $rlRun_LOG
          rlAssertGrep "^exec_prefix" $rlRun_LOG
          rlAssertGrep "^libdir" $rlRun_LOG
          rlAssertGrep "^includedir" $rlRun_LOG
        fi
    rlPhaseEnd

    rlPhaseStartTest "libcap pkg-config should be present and valid"
        rlRun "rpm -ql libcap-devel | grep libpsx.pc" 0 "There must be libpsx.pc"
        if [ $? -eq 0 ]; then
          PCFILE=$(rpm -ql libcap-devel | grep libpsx.pc)
          rlRun "pkg-config --libs libpsx | grep -- '-lpsx'"
          VER=$(awk '/Version:/ { print $2 }' $PCFILE | tail -1)
          rlRun "pkg-config --modversion libpsx | grep $VER"
          rlRun -s "pkg-config --print-variables libpsx"
          rlAssertGrep "^prefix" $rlRun_LOG
          rlAssertGrep "^exec_prefix" $rlRun_LOG
          rlAssertGrep "^libdir" $rlRun_LOG
          rlAssertGrep "^includedir" $rlRun_LOG
        fi
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
