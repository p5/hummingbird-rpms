#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/httpd/Sanity/smoke
#   Description: Simple check of httpd test page
#   Author: Branislav Nater <bnater@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2021 Red Hat, Inc.
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

PACKAGES="${PACKAGES:-httpd}"
REQUIRES=${REQUIRES:-}

rlJournalStart
    rlPhaseStartSetup
        rlRun "rlImport --all" 0 "Importing Beaker libraries" || rlDie
        rlAssertRpm --all
        rlFileBackup --clean ${httpCONFDIR}/conf/
        rlFileBackup --clean ${httpCONFDIR}/conf.d/
        rlFileBackup --clean ${httpCONFDIR}/conf.modules.d/
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "httpStart" 0 "Start httpd"
        rlRun "httpStatus" 0 "Check status"
        rlRun "httpStop" 0 "Stop httpd"

        rlRun "httpSecureStart" 0 "Start httpd with ssl"
        rlRun "httpInstallCa $(hostname)" 0 "Install CA"
        rlRun "httpSecureStatus" 0 "Check status"
        rlRun "httpRemoveCa" 0 "Remove CA"
        rlRun "httpSecureStop" 0 "Stop httpd with ssl"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rlFileRestore" 0 "Restoring original configuration"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
rlJournalPrintText
