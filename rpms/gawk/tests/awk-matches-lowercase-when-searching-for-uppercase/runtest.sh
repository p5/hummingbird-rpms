#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/gawk/Regression/awk-matches-lowercase-when-searching-for-uppercase
#   Description: awk matches lowercase when searching for uppercase
#   Author: Filip Holec <fholec@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2015 Red Hat, Inc.
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
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="gawk"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        OLDLANG=$LANG
        rlRun "pushd $TmpDir"
        rlRun "export LANG=en_US.UTF-8" 0 "Export needed LANG variable"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "echo test | awk '/[A-Z]/' > output" 0 "Run the reproducer"
        cat output
        rlAssertNotGrep "test" output
        rlRun '[ ! -s output ]' 0 "File output should be empty"
        if [ $(echo test | awk --posix '/[A-Z]/' | grep test) ]; then
            rlRun "man gawk | col -bx > gawk.txt" 0 "Get man page in plaintext"
            rlAssertGrep "[A-Z].*will.*also.*match.*the.*lowercase.*characters.*in.*this.*case\!" gawk.txt
        fi
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
        rlRun "export LANG=$OLDLANG" 0 "Restore LANG variable"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
