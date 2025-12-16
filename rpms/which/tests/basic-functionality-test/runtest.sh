#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/which/Sanity/basic-functionality-test
#   Description: tests basic functionality
#   Author: Karel Srot <ksrot@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2017 Red Hat, Inc.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="which"

TRUE_BINARY=/bin/true
BASHBIN=/bin/bash

rlIsRHEL 6 && TRUE_BINARY=/bin/true

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "cp -p $TRUE_BINARY $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest "test --version"
        rlRun "VERSION=\$( rpm -q --qf '%{VERSION}' which )"
        rlRun -s "which --version"
        rlAssertGrep "GNU which v${VERSION}" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "test locating the bash binary"
        rlRun -s "which bash"
        rlAssertGrep "$BASHBIN" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "test an alias"
        rlRun "echo 'alias foo=bar' > bashrc"
        rlRun -s "echo -e 'alias foo=true\nwhich foo' | bash -i"
        rlAssertGrep "alias foo='true'" $rlRun_LOG
        rlAssertGrep "$TRUE_BINARY" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "test non existing command"
        rlRun -s "which foobar" 1
        rlAssertGrep "no foobar in ($PATH)" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "test with customized PATH"
        rlRun -s "bash -c 'export PATH=$TmpDir:$PATH; which true'"
        rlAssertGrep $TmpDir/true $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "test options -a / --all"
        rlRun -s "bash -c 'export PATH=$TmpDir:$PATH; which -a true'"
        rlAssertGrep $TmpDir/true $rlRun_LOG
        rlAssertGrep $TRUE_BINARY $rlRun_LOG
        rlRun -s "bash -c 'export PATH=$TmpDir:$PATH; which --all true'"
        rlAssertGrep $TmpDir/true $rlRun_LOG
        rlAssertGrep $TRUE_BINARY $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
