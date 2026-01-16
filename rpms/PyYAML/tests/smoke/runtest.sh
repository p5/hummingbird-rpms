#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/PyYAML/Sanity/Smoke
#   Description: Smoke test for this component
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
. /usr/share/beakerlib/beakerlib.sh || exit 1

PYTHON=${PYTHON:-"python3"}

PATTERN1="{'name': 'foo'}
{'name': 'bar'}
{'name': 'foobar'}"
PATTERN3="name: Silenthand Olleander
race: Human
traits: [ONE_HAND, ONE_EYE]"
PATTERN4="a: 1
b: {c: 3, d: 4}"
PATTERN5="Hero(name='Welthyr Syxgon', hp=1200, sp=0)"

set -o pipefail

rlJournalStart
    rlPhaseStartSetup
        # export python's MAJOR and MINOR version
        rlRun "export $($PYTHON -c \
                'import sys; print("MAJOR={0} MINOR={1}".format(\
                sys.version_info[0],sys.version_info[1]))')"
    rlPhaseEnd

    rlPhaseStartTest "Running pyyaml_load.py"
        rlRun -s "$PYTHON pyyaml_load.py"
        rlAssertGrep "$PATTERN1" "$rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Running pyyaml_dump.py"
        rlRun -s "$PYTHON pyyaml_dump.py"
        rlAssertGrep "$PATTERN3" "$rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Running pyyaml_parse.py"
        rlRun -s "$PYTHON pyyaml_parse.py"
        rlAssertGrep "$PATTERN4" "$rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Running pyyaml_object.py"
        rlRun -s "$PYTHON pyyaml_object.py"
        rlAssertGrep "$PATTERN5" "$rlRun_LOG"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
