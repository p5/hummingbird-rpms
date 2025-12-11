#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/RFE-support-reading-compressed-ELF-objects
#   Description: Test for BZ#1674430 (RFE support reading compressed ELF objects)
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
KOXZS_TO_TEST=20

rlJournalStart
    rlPhaseStartTest
        # Look to see that dwelf_elf_begin is now in libdw.so
        rlRun "eu-nm -D $(ldd $(which eu-readelf) | awk '/libdw.so/ {print $3}') | fgrep 'dwelf_elf_begin'"
        # Also eu-readelf now takes advantage of dwelf_elf_begin() to directly read compressed ELF files.
        for koxz in $(find /usr/lib/modules/ | fgrep '.ko.xz' | shuf -n $KOXZS_TO_TEST); do
            rlRun "eu-readelf -n $koxz"
        done
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
