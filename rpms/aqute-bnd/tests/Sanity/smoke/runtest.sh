#!/bin/bash
# Author: Mikolaj Izdebski <mizdebsk@redhat.com>
. /usr/share/beakerlib/beakerlib.sh

rlJournalStart

  rlPhaseStartTest "check for presence of bnd command"
    rlAssertRpm aqute-bnd
    rlAssertBinaryOrigin bnd aqute-bnd
  rlPhaseEnd

  rlPhaseStartTest "display bnd version"
    rlRun "bnd version"
  rlPhaseEnd

  rlPhaseStartTest "wrap JAR file as a bundle"
    rlRun "bnd wrap -b foo -v 1.2.3 /usr/share/java/ant/ant-bootstrap.jar"
    rlRun "unzip ant-bootstrap.jar META-INF/MANIFEST.MF"
    rlAssertGrep "^Bundle-SymbolicName:.foo" META-INF/MANIFEST.MF
    rlAssertGrep "^Bundle-Version:.1.2.3" META-INF/MANIFEST.MF
  rlPhaseEnd

rlJournalEnd
rlJournalPrintText
