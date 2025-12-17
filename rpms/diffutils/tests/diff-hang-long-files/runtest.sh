#!/bin/bash
# Author: Michal Fabry <mfabry@redhat.com>

# Copyright (c) 2009 Red Hat, Inc. All rights reserved. This copyrighted material
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

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1


rlJournalStart

# ===================================================================
# Setup - ABORT if some assert fails
# ===================================================================
rlPhaseStartSetup Setup

set -o pipefail

function count_lines() {
  [ ! -r "$1" ] && return 1
  wc -l "$1" | sed "s/^\s*\([0-9]\+\)\s\+.*$/\1/"
}

rlPhaseEnd


# ===================================================================
# Start the test
# ===================================================================
# -------------------------------------------------------------------
# Create connection
rlPhaseStartTest "Create big file"
# -------------------------------------------------------------------

log=$( mktemp /tmp/log.XXXXXX )

rlRun "tr -d \"'\" <words | xargs echo >long-line" 0 "Create big file part 1"
rlRun "for a in \$(seq 30); do cat long-line; done >long-lines" 0 "Create big file part 2"
rlAssertExists 'long-lines'

# -------------------------------------------------------------------
# Test /usr/sbin/ss output
rlPhaseEnd; rlPhaseStartTest "Test diff"
# -------------------------------------------------------------------

log2=$( mktemp /tmp/log.XXXXXX )
now=$(date '+%s')
rlRun "diff -bBw long-lines <(sed -e 's/ /  /' long-lines) >/dev/null"
rlAssertGreater "Less than 150 seconds" 150 `expr $now - $(date '+%s')`

rlPhaseEnd



# ===================================================================
# Start the cleanup
# ===================================================================
rlPhaseStartCleanup Cleanup

rm -f $log $log2 long-line long-lines
rlAssert0 "Remove the log" $?

rlPhaseEnd

#rlCreateLogFromJournal | tee $OUTPUTFILE
rlJournalPrintText
rlJournalEnd
