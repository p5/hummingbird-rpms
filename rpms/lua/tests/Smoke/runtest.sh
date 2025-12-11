#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/lua/Sanity/Smoke
#   Description: Basic smoke for lua component
#   Author: Stepan Sigut <ssigut@redhat.com>
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
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGES=${PACKAGES:-"lua"}
LUA=${LUA:-"lua"}

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm --all
        rlAssertBinaryOrigin $LUA
        set -o pipefail
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "cp *.lua $TmpDir"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "$LUA hello.lua 2>&1 | tee dump.log" 0
        rlAssertGrep "Hello world, from Lua" "dump.log"
    rlPhaseEnd
    rlPhaseStartTest
        rlRun "$LUA bisect.lua 2>&1 | tee dump.log" 0
        rlAssertGrep "after 20 steps, root is 1.3247179985046387 with error 9.5e-07, f=1.8e-07" "dump.log"
    rlPhaseEnd
    rlPhaseStartTest
        rlRun "$LUA globals.lua &>/dev/null" 0
    rlPhaseEnd
    rlPhaseStartTest
        rlRun "$LUA account.lua 2>&1 | tee dump.log" 1
        rlAssertGrep "after creation" "dump.log"
        rlAssertGrep "lua: account.lua:18: insufficient funds on account DEMO" "dump.log"
    rlPhaseEnd
    rlPhaseStartTest
        rlRun "$LUA sieve.lua &>/dev/null" 0
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
