#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/static-relocations-not-known-to-older-linkers
#   Description: static-relocations-not-known-to-older-linkers
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

PACKAGE="elfutils"

rlJournalStart
    rlPhaseStartTest
	relocs=$(mktemp)
	for i in `rpm -ql elfutils-devel`; do readelf -r -W $i; done > $relocs
	# The above is expected to complain about some files not being ELF files,
	# such as *.h files or directories ... ;-)
	rlRun "grep -e GOTPCRELX -e GOT32X $relocs" 1
	# for elfutils-devel-0.170-1.el7.x86_64.rpm, the unwanted relocation is
	# (only) in /usr/lib64/libebl.a
	# readelf -r -W /usr/lib64/libebl.a | grep -e GOTPCRELX -e GOT32X
	# 00000000000001ef  000000250000002a R_X86_64_REX_GOTPCRELX 0000000000000000 stdout - 4
	rm $relocs
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
