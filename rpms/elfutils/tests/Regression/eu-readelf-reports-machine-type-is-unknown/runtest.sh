#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/eu-readelf-reports-machine-type-is-unknown
#   Description: Test for BZ#1724350 (eu-readelf reports machine type is <unknown>)
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

__showgreenlight ()
{
    rlJournalStart
    rlPhaseStartTest
        rlRun "echo \"Irrelevant for $X_SCLS\""
    rlPhaseEnd
    rlJournalEnd
    exit 0
}

echo $X_SCLS | fgrep -q gcc-toolset-9 && __showgreenlight

rlJournalStart
    rlPhaseStartTest
        rlRun "find /usr/lib/firmware/ -name '*.nffw' | xargs eu-readelf -h | awk '/Machine/ {print \$NF}' | fgrep '<unknown>'" 1
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
