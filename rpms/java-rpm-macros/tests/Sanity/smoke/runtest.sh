#!/bin/bash
# Author: Mikolaj Izdebski <mizdebsk@redhat.com>
. /usr/share/beakerlib/beakerlib.sh

rlJournalStart

  rlPhaseStartTest
    rlAssertRpm java-srpm-macros
    rlRun -s "rpm -E '%java_arches'"
    rlAssertGrep "x86_64" $rlRun_LOG
    rlAssertNotGrep "java_arches" $rlRun_LOG
    rlAssertNotGrep "noarch" $rlRun_LOG
    rlRun -s "rpm -E '%buildsystem_maven_install'"
    rlAssertGrep "echo Error: unexpected invocation of a dummy install script" $rlRun_LOG
    rlRun -s "rpm -E '%buildsystem_maven_generate_buildrequires'"
    rlAssertGrep "echo dola" $rlRun_LOG
    rlAssertNotGrep "javapackages-bootstrap" $rlRun_LOG
    rlRun -s "rpm -E '%{buildsystem_maven_conf -- usesJavapackagesBootstrap};%{buildsystem_maven_generate_buildrequires}'"
    rlAssertGrep ";echo dola" $rlRun_LOG
    rlAssertNotGrep "javapackages-bootstrap" $rlRun_LOG
    rlRun -s "rpm -E '%{bcond bootstrap 1};%{buildsystem_maven_generate_buildrequires}'"
    rlAssertGrep ";echo dola" $rlRun_LOG
    rlAssertNotGrep "javapackages-bootstrap" $rlRun_LOG
    rlRun -s "rpm -E '%{bcond bootstrap 1}%{buildsystem_maven_conf -- usesJavapackagesBootstrap};%{buildsystem_maven_generate_buildrequires}'"
    rlAssertGrep ";echo javapackages-bootstrap" $rlRun_LOG
    rlAssertNotGrep "dola" $rlRun_LOG
    rlRun -s "rpm -E '%{bcond bootstrap 0}%{buildsystem_maven_conf -- usesJavapackagesBootstrap};%{buildsystem_maven_generate_buildrequires}'"
    rlAssertGrep ";echo dola" $rlRun_LOG
    rlAssertNotGrep "javapackages-bootstrap" $rlRun_LOG
  rlPhaseEnd

rlJournalEnd
rlJournalPrintText
