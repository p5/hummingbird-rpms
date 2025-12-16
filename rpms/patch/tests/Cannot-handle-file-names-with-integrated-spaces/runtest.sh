#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/patch/Regression/Cannot-handle-file-names-with-integrated-spaces
#   Description: Test for bz431887 (Cannot handle file names with integrated spaces)
#   Author: Ondrej Moris <omoris@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2010 Red Hat, Inc. All rights reserved.
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

# Include rhts environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="patch"

function apply_patch {
expect <<EOF
set timeout 5
spawn patch -i spaces.patch
expect "patching file 'f i r s t'" { expect timeout ; exit 0 }
exit 1
EOF
return $?
}

rlJournalStart

    rlPhaseStartSetup

        rlAssertRpm $PACKAGE

    rlPhaseEnd

    rlPhaseStartTest

        rlRun "echo \"1\" > \"f i r s t\"" 0
        rlRun "echo \"2\" > \"s e c o n d\"" 0
        rlAssertExists "f i r s t"
        rlAssertExists "s e c o n d"
        rlAssertDiffer "f i r s t" "s e c o n d"
        rlRun "diff -u f\ i\ r\ s\ t s\ e\ c\ o\ n\ d > spaces.patch" 1
        rlRun "apply_patch" 0 "Patching file with spaces in its name"
        rlAssertExists "f i r s t"
        rlAssertExists "s e c o n d"
        rlAssertNotDiffer "f i r s t" "s e c o n d"

    rlPhaseEnd

    rlPhaseStartCleanup

        rlRun "rm -f f\ i\ r\ s\ t s\ e\ c\ o\ n\ d spaces.patch"

    rlPhaseEnd

rlJournalPrintText

rlJournalEnd
