#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/add-ppc64-fallback-unwinder
#   Description: add-ppc64-fallback-unwinder
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2017 Red Hat, Inc.
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
        rlAssertRpm $PACKAGE
        rlRun "TEMPD=\$(mktemp -d)"
        rlRun "cp backtrace.ppc64le.fp.core.bz2 backtrace.ppc64le.fp.exec.bz2 output.ref $TEMPD"
        rlRun "pushd $TEMPD"
        rlRun "bunzip2 backtrace.ppc64le.fp.core.bz2"
        rlRun "bunzip2 backtrace.ppc64le.fp.exec.bz2"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "eu-stack --exec backtrace.ppc64le.fp.exec --core backtrace.ppc64le.fp.core |& tee output.txt"
        rlRun "grep '^#' output.ref > output.ref.filtered"
        rlRun "grep '^#' output.txt > output.txt.filtered"
        rlRun "diff output.txt.filtered output.ref.filtered"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TEMPD"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
