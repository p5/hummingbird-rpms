#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/source-highlight/Sanity/source-highlight-testsuite
#   Description: source-highlight testing by upstream testsuite
#   Author: Michal Kolar <mkolar@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2021 Red Hat, Inc.
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

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

BUILD_USER=${BUILD_USER:-srchghlghtbld}
TESTS_COUNT_MIN=${TESTS_COUNT_MIN:-100}
PACKAGE="source-highlight"
REQUIRES="$PACKAGE rpm-build gcc-c++"
if rlIsFedora; then
  REQUIRES="$REQUIRES dnf-utils"
else
  REQUIRES="$REQUIRES yum-utils"
fi

rlJournalStart
  rlPhaseStartSetup
    rlShowRunningKernel
    rlAssertRpm --all
    rlRun "TmpDir=\$(mktemp -d)"
    rlRun "pushd $TmpDir"
    rlFetchSrcForInstalled $PACKAGE
    rlRun "useradd -M -N $BUILD_USER" 0,9
    [ "$?" == "0" ] && rlRun "del=yes"
    rlRun "chown -R $BUILD_USER:users $TmpDir"
  rlPhaseEnd

  rlPhaseStartSetup "build source-highlight"
    rlRun "rpm -D \"_topdir $TmpDir\" -U *.src.rpm"
    rlRun "yum-builddep -y $TmpDir/SPECS/*.spec"
    rlRun "su -c 'rpmbuild -D \"_topdir $TmpDir\" -bp --undefine specpartsdir $TmpDir/SPECS/*.spec &>$TmpDir/rpmbuild.log' $BUILD_USER"
    rlRun "rlFileSubmit $TmpDir/rpmbuild.log"
    rlRun "cd $TmpDir/BUILD/source-highlight-*"
    rlRun "su -c './configure --build=`arch`-redhat-linux-gnu &>$TmpDir/configure.log' $BUILD_USER"
    rlRun "rlFileSubmit $TmpDir/configure.log"
    rlRun "cd tests"
  rlPhaseEnd

  rlPhaseStartTest "run testsuite"
    rlRun "su -c 'make -k PROGEXE=`which source-highlight` check &>$TmpDir/testsuite.log' $BUILD_USER"
    rlRun "rlFileSubmit $TmpDir/testsuite.log"
  rlPhaseEnd

  rlPhaseStartTest "evaluate results"
    rlRun "cd $TmpDir"
    rlRun "grep -E 'Makefile.+Error' testsuite.log" 1
    rlRun "tests_count=\$(grep -E '^`which source-highlight`' testsuite.log | wc -l)"
    [ "$tests_count" -ge "$TESTS_COUNT_MIN" ] && rlLogInfo "Test counter: $tests_count" || rlFail "Test counter $tests_count should be greater than or equal to $TESTS_COUNT_MIN"
  rlPhaseEnd

  rlPhaseStartCleanup
    rlRun "popd"
    rlRun "rm -r $TmpDir"
    [ "$del" == "yes" ] && rlRun "userdel $BUILD_USER"
  rlPhaseEnd
rlJournalPrintText
rlJournalEnd
