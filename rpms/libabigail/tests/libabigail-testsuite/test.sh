#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

BUILD_USER=${BUILD_USER:-lbbglbld}
TESTS_COUNT_MIN=${TESTS_COUNT_MIN:-10}
PACKAGE="libabigail"
REQUIRES="$PACKAGE rpm-build gcc-c++"
if rlIsFedora; then
  REQUIRES="$REQUIRES dnf-utils"
else
  REQUIRES="$REQUIRES yum-utils"
fi

# variables needed for 'make check'
export RPM_PACKAGE_NAME=$(rpm -q --qf='%{NAME}\n' $PACKAGE)
export RPM_PACKAGE_VERSION=$(rpm -q --qf='%{VERSION}\n' $PACKAGE)
export RPM_PACKAGE_RELEASE=$(rpm -q --qf='%{RELEASE}\n' $PACKAGE)
export RPM_ARCH=$(rpm -q --qf='%{ARCH}\n' $PACKAGE)

rlJournalStart
  rlPhaseStartSetup
    rlShowRunningKernel
    rlAssertRpm --all
    rlRun "TmpDir=\$(mktemp -d /home/libabigail.XXXXXXXXXX)"  # work in /home due to high demands on disk space
    rlRun "pushd $TmpDir"
    rlFetchSrcForInstalled $PACKAGE
    rlRun "useradd -N $BUILD_USER" 0,9
    [ "$?" == "0" ] && rlRun "del=yes"
    rlRun "chown -R $BUILD_USER:users $TmpDir"
  rlPhaseEnd

  rlPhaseStartSetup "build libabigail"
    rlRun "rpm -D \"_topdir $TmpDir\" -U *.src.rpm"
    rlRun "yum-builddep -y $TmpDir/SPECS/*.spec &>$TmpDir/yum-builddep.log"
    rlRun "rlFileSubmit $TmpDir/yum-builddep.log yum-builddep.log"
    rlRun "su -c 'rpmbuild -D \"_topdir $TmpDir\" -bc $TmpDir/SPECS/*.spec &>$TmpDir/rpmbuild.log' $BUILD_USER"
    rlRun "rlFileSubmit $TmpDir/rpmbuild.log rpmbuild.log"
    rlRun "cd $(dirname `find $TmpDir -name configure -type f`)"
  rlPhaseEnd

  rlPhaseStartTest "run testsuite"
    rlRun "su -c 'make check |& tee $TmpDir/testsuite.log' $BUILD_USER"
    rlRun "rlFileSubmit tests/test-suite.log test-suite.log"
    rlRun "rlFileSubmit $TmpDir/testsuite.log testsuite.log"
  rlPhaseEnd

  rlPhaseStartTest "evaluate results"
    rlRun "grep -E '^# FAIL:|^# XPASS:|^# ERROR:' $TmpDir/testsuite.log | grep -vqE ':\s*0$'" 1
    rlRun "tests_count=\$(grep -E '^PASS:' $TmpDir/testsuite.log | wc -l)"
    [ "$tests_count" -ge "$TESTS_COUNT_MIN" ] && rlLogInfo "Test counter: $tests_count" || rlFail "Test counter $tests_count should be greater than or equal to $TESTS_COUNT_MIN"
  rlPhaseEnd

  rlPhaseStartCleanup
    rlRun "popd"
    rlRun "rm -r $TmpDir"
    [ "$del" == "yes" ] && rlRun "userdel -f -r $BUILD_USER"
  rlPhaseEnd
rlJournalPrintText
rlJournalEnd
