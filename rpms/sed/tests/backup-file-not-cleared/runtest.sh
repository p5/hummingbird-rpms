#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/sed/Regression/backup-file-not-cleared
#   Description: Test for tmp file not clear after registered to rhevm
#   Author: Petr Muller <pmuller@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
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

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh

PACKAGE="sed"

rlJournalStart
  rlPhaseStartSetup
    rlRun "mkdir TMP"
    rlRun "cd TMP"
    rlRun "echo 'some content' > somefile"
    rlRun "echo 'changed content' > somefile-expected"
    rlRun "touch filelist"
    cat > filelist-golden << EOF
./filelist
./filelist-golden
./somefile
./somefile-expected
EOF
  rlPhaseEnd

  rlPhaseStartTest
    rlRun "sed -i --copy 's/some/changed/' somefile"
    rlRun "find . -type f | sort -f > filelist"

    rlAssertNotDiffer filelist filelist-golden
    if [ $? -ne 0 ]
    then
      rlLog "Differences found: "
      diff -u filelist-golden filelist | while read line
      do
        rlLog "\"$line\""
      done
    fi

    rlAssertNotDiffer somefile somefile-expected
    if [ $? -ne 0 ]
    then
      rlLog "Differences found: "
      diff -u somefile-expected somefile | while read line
      do
        rlLog "\"$line\""
      done
    fi

    rlRun "rm -f sed*"
    rlRun "echo 'some content' > somefile"
    rlRun "sed -i-fxpected --copy 's/some/changed/' somefile"
    rlRun "find . -type f | sort > filelist"
    echo "./somefile-fxpected" >> filelist-golden
    rlAssertExists somefile-fxpected
    sort filelist-golden -o filelist-golden

    rlAssertNotDiffer filelist filelist-golden
    if [ $? -ne 0 ]
    then
      rlLog "Differences found: "
      diff -u filelist-golden filelist | while read line
      do
        rlLog "\"$line\""
      done
    fi

    rlAssertNotDiffer somefile somefile-expected
    if [ $? -ne 0 ]
    then
      rlLog "Differences found: "
      diff -u somefile-expected somefile | while read line
      do
        rlLog "\"$line\""
      done
    fi
  rlPhaseEnd

  rlPhaseStartCleanup
    rlRun "cd .."
    rlRun "rm -rf TMP"
  rlPhaseEnd
rlJournalEnd
