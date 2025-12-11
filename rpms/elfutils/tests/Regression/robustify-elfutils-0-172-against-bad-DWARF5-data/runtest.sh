#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/robustify-elfutils-0-172-against-bad-DWARF5-data
#   Description: Test for BZ#1593328 (Robustify elfutils 0.172 against bad DWARF5 data)
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2018 Red Hat, Inc.
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

_sections="abbrev addr aranges decodedaranges frame gdb_index info info+ loc \
line decodedline ranges pubnames str macinfo macro exception"

rlJournalStart
    rlPhaseStartTest
	for _data in crashes/*; do
	    for _section in $_sections; do
		# 0 and 1 are expected exitcodes:
		rlRun "timeout 7 eu-readelf --debug-dump=$_section $_data >/dev/null" 0,1
	    done
	done
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
