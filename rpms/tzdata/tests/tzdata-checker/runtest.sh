#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tzdata/Sanity/tzdata-checker
#   Description: Testing tzdata by comparing base pkg with upstream
#   Author: Michal Kolar <mkolar@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2018 Red Hat, Inc.
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation, either version 2 of
#   the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see http://www.gnu.org/licenses/.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if [ "$NO_BEAKERLIB" == "1" ]; then
  . ./no-beakerlib-wrapper.sh || exit 1
else
  # Include Beaker environment
  . /usr/share/beakerlib/beakerlib.sh || exit 1
fi

PACKAGE="tzdata"
TZDATA_URL="https://data.iana.org/time-zones/releases"
TZDATA_VERSION="${TZDATA_VERSION:-$(rpm -q --qf '%{VERSION}\n' $PACKAGE | head -1)}"
if rlIsFedora; then
  DATAFORM="${DATAFORM:-vanguard}"
else
  DATAFORM="${DATAFORM:-rearguard}"
fi
YEARS=20  # used for shrink zdump output to reasonable future

hiyear=$((`date +%Y` + $YEARS))
export LC_ALL=C

rlJournalStart
  rlPhaseStartSetup
    rlShowRunningKernel
    rlAssertRpm $PACKAGE
    rlRun "TmpDir=\$(mktemp -d)"
    rlRun "cp zones.min $TmpDir"
    rlRun "pushd $TmpDir"
    rlRun "mkdir badzones"
  rlPhaseEnd

  rlPhaseStartSetup "Build upstream tzdata"  # source: https://data.iana.org/time-zones/tz-link.html
    rlRun "wget --no-check-certificate ${TZDATA_URL}/tzcode${TZDATA_VERSION}.tar.gz"
    rlRun "wget --no-check-certificate ${TZDATA_URL}/tzdata${TZDATA_VERSION}.tar.gz"
    rlRun "tar -xzf tzcode*"
    rlRun "tar -xzf tzdata*"

    rlRun "make DATAFORM=$DATAFORM TOPDIR=./tzdir install"
    rlRun "find tzdir/usr/share/zoneinfo -type f | xargs file | grep 'timezone data' | grep -o -E 'zoneinfo/[^:]+' | sed 's|zoneinfo/||' | sort -u >zones.ref"
    rlRun "find /usr/share/zoneinfo -type f | xargs file | grep 'timezone data' | grep -o -E 'zoneinfo/[^:]+' | sed 's|zoneinfo/||' | sort -u >zones.cur"
    rlRun "comm -12 zones.ref  zones.cur >zones.int"  # intersection of ref zones with cur zones
    rlRun "sort -u zones.min >zones-sorted.min"
    rlRun "comm -13 zones.int zones-sorted.min >zones.mis"
    rlRun "if [ -s ./zones.mis ]; then cat ./zones.mis; false; fi"
    rlLogInfo "Number of time zones: `cat zones.int | wc -l`"
  rlPhaseEnd

  rlPhaseStartSetup "Test zdump"
    for zone in `cat zones.int`; do
      if rlIsRHEL "<8"; then # glibc's zdump is out of sync for '-v option'
        rlRun "./zdump -v -c 1970,$hiyear $zone >ref"
        rlRun "./zdump -v -c 1970,$hiyear /usr/share/zoneinfo/$zone >cur"
        sed -i 's|^/usr/share/zoneinfo/||' cur
      else
        rlRun "./zdump -V -c 1970,$hiyear $zone >ref"
        rlRun "zdump -V -c 1970,$hiyear $zone >cur"
      fi

      # normalize zdump outputs
      sed -i 's/\ UTC/\ UT/g' ref cur

      if ! rlRun "diff -q ref cur"; then
        filezone=`echo $zone | tr '/' '_'`
        cp ref ./badzones/${filezone}.ref
        cp cur ./badzones/${filezone}.cur
      fi
    done
  rlPhaseEnd

  rlPhaseStartCleanup
    rlRun "tar -czf badzones.tar.gz ./badzones"
    rlRun "rlFileSubmit badzones.tar.gz"
    rlRun "popd"
    rlRun "rm -r $TmpDir"
  rlPhaseEnd
rlJournalPrintText
rlJournalEnd
