#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/findutils/Sanity/smoke
#   Description: Smoke test for find and xargs.
#   Author: Branislav Nater <bnater@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2014 Red Hat, Inc. All rights reserved.
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

PACKAGE="findutils"

rlJournalStart
  rlPhaseStartSetup
    rlAssertRpm $PACKAGE
    rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
    rlRun "pushd $TmpDir"
    rlRun "touch \"file with spaces\"" 0
    rlRun "mkdir dir" 0
    rlRun "touch dir/file1" 0
  rlPhaseEnd

  rlGetTestState && {
    rlPhaseStartTest
      rlRun "find . -name \"file*\" -type f | tee output | wc -l > wcout" 0
      cat output
      rlAssertGrep 2 wcout
      rlRun "find $TmpDir -mindepth 1 -type d | tee output | wc -l > wcout" 0
      cat output
      rlAssertGrep 1 wcout
      rlRun "find $TmpDir -name \"file*\" -print0 | xargs -0 ls -l | tee output | wc -l > wcout" 0
      cat output
      rlAssertGrep 2 wcout
    rlPhaseEnd
  }

  rlPhaseStartCleanup
    rlRun "popd"
    rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
  rlPhaseEnd
rlJournalEnd
rlJournalPrintText
