#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tzdata"
REQUIRES="$PACKAGE coreutils glibc"
export LC_TIME=C

rlJournalStart
  rlPhaseStartSetup
    rlShowRunningKernel
    rlAssertRpm --all
    rlRun "TmpDir=\$(mktemp -d)"
    rlRun "cp zones datetimes date.golden $TmpDir"
    rlRun "pushd $TmpDir"
  rlPhaseEnd

  rlPhaseStartTest "run test"
    while read timezone; do
      rlLogInfo "timezone: $timezone"
      while read datetime; do
	echo -n "$timezone $datetime -> " >>date.log
        rlRun "TZ=$timezone date -d \"$datetime\" >>date.log"
      done <datetimes
    done <zones
    rlRun "rlFileSubmit ./date.log date.log"
  rlPhaseEnd

  rlPhaseStartTest "evaluate results"
    if ! rlRun "diff -u date.golden date.log >date.diff"; then
      rlFail "Differences observed";
      rlRun "rlFileSubmit ./date.diff date.diff"
    fi    
  rlPhaseEnd

  rlPhaseStartCleanup
    rlRun "popd"
    rlRun "rm -r $TmpDir"
  rlPhaseEnd
rlJournalPrintText
rlJournalEnd
