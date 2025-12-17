#!/bin/sh

# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Bill Peck

. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="diffutils"

rlJournalStart
  rlPhaseStartSetup
    rlAssertRpm $PACKAGE
    rlRun "TmpDir=\`mktemp -d\`" 0 "Creating tmp directory"
  rlPhaseEnd

  rlPhaseStartTest
    rlRun "diff -b file1 file2"
  rlPhaseEnd

  rlPhaseStartCleanup
    rlRun "rm -fr $TmpDir" 0 "Removing tmp directory"
  rlPhaseEnd
rlJournalEnd
rlJournalPrintText
