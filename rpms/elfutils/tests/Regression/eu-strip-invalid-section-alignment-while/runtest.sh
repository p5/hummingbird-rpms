#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/eu-strip-invalid-section-alignment-while
#   Description: eu-strip-invalid-section-alignment-while
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2016 Red Hat, Inc.
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
        for p in gcc eu-strip; do
            rlRun "which $p"
            rlRun "rpm -qf $( which $p )"
        done
        rlRun "tmp=$(mktemp -d)"
        rlRun "cp testprog.c testprog2.c $tmp" 
        rlRun "pushd $tmp"
    rlPhaseEnd

    if rpm -q libaio-devel; then
        rlPhaseStart FAIL customer-testcase
            # https://bugzilla.redhat.com/show_bug.cgi?id=1304870
            rlRun "gcc testprog.c -laio -g -o testprog"
            rlRun "eu-strip testprog"
        rlPhaseEnd
    fi

    rlPhaseStart FAIL upstream-testcase
        rlRun "gcc -g testprog2.c -o testprog2"
        # Testcase for this fix should at some point reach the upstream and
        # the rhel package too. After that this QE testcase should be obsoleted.
        # Please, refer to:
        # https://lists.fedorahosted.org/archives/list/elfutils-devel@lists.fedorahosted.org/message/OP6AXOW5PF6GPB4KN7XQZSZ5JY6RK52U/
        rlRun "eu-strip testprog2"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
