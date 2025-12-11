#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Sanity/elfutils-debuginfod
#   Description: elfutils-debuginfod
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2019 Red Hat, Inc.
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

PACKAGE="elfutils"

rlJournalStart
    rlPhaseStartSetup
        for p in elfutils-debuginfod elfutils-debuginfod-client; do
            rlAssertRpm $p
        done
        rlRun "TMPD=$(mktemp -d)"
        rlRun "cp body.sh sshpass-debuginfo-1.09-2.fc35.x86_64.rpm $TMPD"
        rlRun "pushd $TMPD"
        rlFileBackup /etc/sysconfig/debuginfod
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "./body.sh"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlFileRestore
        rlRun "popd"
        rlRun "rm -r $TMPD"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
