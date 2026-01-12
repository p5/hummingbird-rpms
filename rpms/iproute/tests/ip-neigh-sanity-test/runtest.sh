#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/iproute/Sanity/ip-neigh-sanity-test
#   Description: Test basic ip neigh funcionality
#   Author: Jaroslav Aster <jaster@redhat.com>
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

# Include Beaker environment
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="iproute"
TEST_IFACE="test-iface"
TEST_IP4_PREFIX="192.168.100"
TEST_IP6_PREFIX="2000::"
TEST_MAC_PREFIX="00:c0:7b:7d:00"
rlIsRHEL '>=7' && MAN_PAGE="ip-neighbour" || MAN_PAGE="ip"
MESSAGES="/var/log/messages"
TMP_MESSAGES="$(mktemp)"


create_dummy_iface()
{
    rlRun "ip link add name ${TEST_IFACE} type dummy" 0 "Creating dummy interface: '${TEST_IFACE}'."
}

delete_dummy_iface()
{
    rlRun "ip link del ${TEST_IFACE}" 0 "Removing dummy interface: '${TEST_IFACE}'."
    rlRun "rmmod dummy" 0,1 "Removing dummy module."
}


rlJournalStart
    rlPhaseStartSetup
        rlCheckRpm "$PACKAGE"
        create_dummy_iface
    rlPhaseEnd

    if rlIsRHEL '>=7'; then
        rlPhaseStartTest
            for word in add del change replace show flush all proxy to dev nud unused permanent reachable probe failed incomplete stale delay noarp none; do
		if ! { [ "$word" = "unused" ] || [ "$word" = "all" ]; }; then
                    rlRun "ip n help 2>&1 | grep -e '[^[:alnum:]]${word}[^[:alnum:]]'" 0 "Checking there is '${word}' in ip neighbour help."
		fi
                rlRun "man ${MAN_PAGE} | col -b | grep -e '[^[:alnum:]]${word}[^[:alnum:]]'" 0 "Checking there is '${word}' in ${MAN_PAGE} man page."
            done
        rlPhaseEnd
    fi

    rlPhaseStartTest "Functional Test"
        rlLogInfo "IPv4"
        rlRun "ip neigh add ${TEST_IP4_PREFIX}.1 lladdr ${TEST_MAC_PREFIX}:c6 dev ${TEST_IFACE} nud permanent"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.1 | grep 'PERMANENT'"

        rlRun "ip neigh add ${TEST_IP4_PREFIX}.2 lladdr ${TEST_MAC_PREFIX}:c7 dev ${TEST_IFACE}"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.2 | grep 'PERMANENT'"

        rlRun "ip neigh add ${TEST_IP4_PREFIX}.3 lladdr ${TEST_MAC_PREFIX}:c8 dev ${TEST_IFACE} nud noarp"
        rlRun "ip neigh show nud all ${TEST_IP4_PREFIX}.3 | grep 'NOARP'"

        rlRun "ip neigh add ${TEST_IP4_PREFIX}.4 lladdr ${TEST_MAC_PREFIX}:c9 dev ${TEST_IFACE} nud noarp"
        rlRun "ip neigh show nud all ${TEST_IP4_PREFIX}.4 | grep 'NOARP'"

        rlRun "ip neigh add lladdr ${TEST_MAC_PREFIX}:ce dev ${TEST_IFACE} proxy ${TEST_IP4_PREFIX}.10"
        rlIsRHEL ">=7" && rlRun "ip neigh show proxy | grep ${TEST_IP4_PREFIX}.10"

        rlRun "test $(ip neigh show dev ${TEST_IFACE} | wc -l) -eq 2" 0 "There are two items in neighbours."

        rlRun "ip neigh del ${TEST_IP4_PREFIX}.1 dev ${TEST_IFACE}"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.1 | grep 'FAILED'"

        rlRun "ip neigh change ${TEST_IP4_PREFIX}.2 lladdr ${TEST_MAC_PREFIX}:ca dev ${TEST_IFACE} nud reachable"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.2 | grep 'REACHABLE'"

        rlRun "ip neigh replace ${TEST_IP4_PREFIX}.3 lladdr ${TEST_MAC_PREFIX}:cb dev ${TEST_IFACE} nud permanent"
        rlRun "ip neigh show nud all ${TEST_IP4_PREFIX}.3 | grep 'PERMANENT'"

        rlRun "test $(ip neigh show dev ${TEST_IFACE} nud permanent | wc -l) -eq 1" 0 "There is one permanent item in neighbours."
        rlRun "test $(ip neigh show dev ${TEST_IFACE} nud reachable | wc -l) -eq 1" 0 "There is one reachable item in neighbours."
        rlRun "test $(ip neigh show dev ${TEST_IFACE} nud noarp | wc -l) -eq 1" 0 "There is one noarp item in neighbours."
        rlRun "test $(ip neigh show dev ${TEST_IFACE} nud failed | wc -l) -eq 1" 0 "There is one failed item in neighbours."
        rlIsRHEL ">=7" && rlRun "test $(ip neigh show dev ${TEST_IFACE} proxy | wc -l) -eq 1" 0 "There is one proxy item in neighbours."
        rlRun "test $(ip neigh show dev ${TEST_IFACE} | grep -e PERMANENT -e REACHABLE -e FAILED | wc -l) -eq 3" 0 "There are three permanent or reachable or failed items in neighbours."

        rlRun "ip neigh show dev ${TEST_IFACE} unused"

        rlRun "ip neigh change ${TEST_IP4_PREFIX}.4 dev ${TEST_IFACE} nud delay"
        rlRun "ip neigh flush ${TEST_IP4_PREFIX}.4 dev ${TEST_IFACE}"
        rlRun "ip neigh show nud all | grep '${TEST_IP4_PREFIX}.4'"

        rlRun "ip -s neigh flush ${TEST_IP4_PREFIX}.4 dev ${TEST_IFACE}"
        rlRun "ip -s -s neigh flush ${TEST_IP4_PREFIX}.4 dev ${TEST_IFACE}"

        rlRun "ip neigh add ${TEST_IP4_PREFIX}.11 lladdr ${TEST_MAC_PREFIX}:c8 dev ${TEST_IFACE} nud permanent"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.11 | grep 'PERMANENT'"

        rlRun "ip neigh change ${TEST_IP4_PREFIX}.11 dev ${TEST_IFACE} nud reachable"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.11 | grep 'REACHABLE'"

        rlRun "ip neigh change ${TEST_IP4_PREFIX}.11 dev ${TEST_IFACE} nud probe"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.11 | grep 'PROBE'"

        rlRun "ip neigh change ${TEST_IP4_PREFIX}.11 lladdr ${TEST_MAC_PREFIX}:c9 dev ${TEST_IFACE} nud failed"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.11 | grep 'FAILED'"

        rlRun "ip neigh change ${TEST_IP4_PREFIX}.11 dev ${TEST_IFACE} nud incomplete"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.11 | grep 'INCOMPLETE'"

        rlRun "ip neigh replace ${TEST_IP4_PREFIX}.11 lladdr ${TEST_MAC_PREFIX}:cb dev ${TEST_IFACE} nud stale"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.11 | grep '${TEST_MAC_PREFIX}:cb' | grep 'STALE'"

        rlRun "ip neigh replace ${TEST_IP4_PREFIX}.11 dev ${TEST_IFACE} nud delay"
        rlRun "ip neigh show ${TEST_IP4_PREFIX}.11 | grep -e 'DELAY' -e 'PROBE'"

        rlRun "ip neigh replace ${TEST_IP4_PREFIX}.11 dev ${TEST_IFACE} nud noarp"
        rlRun "ip neigh show nud all ${TEST_IP4_PREFIX}.11 | grep 'NOARP'"

        rlRun "ip neigh change ${TEST_IP4_PREFIX}.11 dev ${TEST_IFACE} nud none"
        rlRun "ip neigh show nud none | grep ${TEST_IP4_PREFIX}.11"

        rlRun "ip neigh show ${TEST_IP4_PREFIX}.0/24"

        rlLogInfo "IPv6"
        rlRun "ip -6 neigh add ${TEST_IP6_PREFIX}1 lladdr ${TEST_MAC_PREFIX}:c6 dev ${TEST_IFACE} nud permanent"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}1 | grep 'PERMANENT'"

        rlRun "ip -6 neigh add ${TEST_IP6_PREFIX}2 lladdr ${TEST_MAC_PREFIX}:c7 dev ${TEST_IFACE}"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}2 | grep 'PERMANENT'"

        rlRun "ip -6 neigh add ${TEST_IP6_PREFIX}3 lladdr ${TEST_MAC_PREFIX}:c8 dev ${TEST_IFACE} nud noarp"
        rlRun "ip -6 neigh show nud all ${TEST_IP6_PREFIX}3 | grep 'NOARP'"

        rlRun "ip -6 neigh add ${TEST_IP6_PREFIX}4 lladdr ${TEST_MAC_PREFIX}:c9 dev ${TEST_IFACE} nud noarp"
        rlRun "ip -6 neigh show nud all ${TEST_IP6_PREFIX}4 | grep 'NOARP'"

        rlRun "ip -6 neigh add lladdr ${TEST_MAC_PREFIX}:ce dev ${TEST_IFACE} proxy ${TEST_IP6_PREFIX}10"
        rlIsRHEL ">=7" && rlRun "ip -6 neigh show proxy | grep ${TEST_IP6_PREFIX}10"

        rlRun "test $(ip -6 neigh show dev ${TEST_IFACE} | wc -l) -eq 2" 0 "There are two items in neighbours."

        rlRun "ip -6 neigh del ${TEST_IP6_PREFIX}1 dev ${TEST_IFACE}"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}1 | grep 'FAILED'"

        rlRun "ip -6 neigh change ${TEST_IP6_PREFIX}2 lladdr ${TEST_MAC_PREFIX}:ca dev ${TEST_IFACE} nud reachable"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}2 | grep 'REACHABLE'"

        rlRun "ip -6 neigh replace ${TEST_IP6_PREFIX}3 lladdr ${TEST_MAC_PREFIX}:cb dev ${TEST_IFACE} nud permanent"
        rlRun "ip -6 neigh show nud all ${TEST_IP6_PREFIX}3 | grep 'PERMANENT'"

        rlRun "test $(ip -6 neigh show dev ${TEST_IFACE} nud permanent | wc -l) -eq 1" 0 "There is one permanent item in neighbours."
        rlRun "test $(ip -6 neigh show dev ${TEST_IFACE} nud reachable | wc -l) -eq 1" 0 "There is one reachable item in neighbours."
        rlRun "test $(ip -6 neigh show dev ${TEST_IFACE} nud noarp | wc -l) -eq 1" 0 "There is one noarp item in neighbours."
        rlRun "test $(ip -6 neigh show dev ${TEST_IFACE} nud failed | wc -l) -eq 1" 0 "There is one failed item in neighbours."
        rlIsRHEL ">=7" && rlRun "test $(ip -6 neigh show dev ${TEST_IFACE} proxy | wc -l) -eq 1" 0 "There is one proxy item in neighbours."
        rlRun "test $(ip -6 neigh show dev ${TEST_IFACE} | grep -e PERMANENT -e REACHABLE -e FAILED | wc -l) -eq 3" 0 "There are three permanent or reachable or failed items in neighbours."

        rlRun "ip -6 neigh show dev ${TEST_IFACE} unused"

        rlRun "ip -6 neigh change ${TEST_IP6_PREFIX}4 dev ${TEST_IFACE} nud delay"
        rlRun "ip -6 neigh flush ${TEST_IP6_PREFIX}4 dev ${TEST_IFACE}"
        rlRun "ip -6 neigh show nud all | grep '${TEST_IP6_PREFIX}4'"

        rlRun "ip -6 -s neigh flush ${TEST_IP6_PREFIX}4 dev ${TEST_IFACE}"
        rlRun "ip -6 -s -s neigh flush ${TEST_IP6_PREFIX}4 dev ${TEST_IFACE}"

        rlRun "ip -6 neigh add ${TEST_IP6_PREFIX}11 lladdr ${TEST_MAC_PREFIX}:c8 dev ${TEST_IFACE} nud permanent"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}11 | grep 'PERMANENT'"

        rlRun "ip -6 neigh change ${TEST_IP6_PREFIX}11 dev ${TEST_IFACE} nud reachable"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}11 | grep 'REACHABLE'"

        rlRun "ip -6 neigh change ${TEST_IP6_PREFIX}11 dev ${TEST_IFACE} nud probe"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}11 | grep 'PROBE'"

        rlRun "ip -6 neigh change ${TEST_IP6_PREFIX}11 lladdr ${TEST_MAC_PREFIX}:c9 dev ${TEST_IFACE} nud failed"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}11 | grep 'FAILED'"

        rlRun "ip -6 neigh change ${TEST_IP6_PREFIX}11 dev ${TEST_IFACE} nud incomplete"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}11 | grep 'INCOMPLETE'"

        rlRun "ip -6 neigh replace ${TEST_IP6_PREFIX}11 lladdr ${TEST_MAC_PREFIX}:cb dev ${TEST_IFACE} nud stale"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}11 | grep '${TEST_MAC_PREFIX}:cb' | grep 'STALE'"

        rlRun "ip -6 neigh replace ${TEST_IP6_PREFIX}11 dev ${TEST_IFACE} nud delay"
        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}11 | grep -e 'DELAY' -e 'PROBE'"

        rlRun "ip -6 neigh replace ${TEST_IP6_PREFIX}11 dev ${TEST_IFACE} nud noarp"
        rlRun "ip -6 neigh show nud all ${TEST_IP6_PREFIX}11 | grep 'NOARP'"

        rlRun "ip -6 neigh change ${TEST_IP6_PREFIX}11 dev ${TEST_IFACE} nud none"
        rlRun "ip -6 neigh show nud none | grep ${TEST_IP6_PREFIX}11"

        rlRun "ip -6 neigh show ${TEST_IP6_PREFIX}0/24"
    rlPhaseEnd

    rlPhaseStartTest
        pushd /tmp # because of coredump file
        tail -f -n 0 "$MESSAGES" > "$TMP_MESSAGES" &
        tail_pid="$!"
        rlRun "ip neigh add ${TEST_IP4_PREFIX}.11 lladdr ${TEST_MAC_PREFIX}:c16 dev ${TEST_IFACE} nud permanent" 1,255
        kill "$tail_pid"
        rlRun "grep -i -e 'segfault' -e 'unhandled signal' -e 'User process fault' ${TMP_MESSAGES}" 1 "Checking there is no segfault in /var/log/messages."
        popd
    rlPhaseEnd

    rlPhaseStartCleanup
        delete_dummy_iface
        rlRun "rm ${TMP_MESSAGES}" 0 "Removing tmp files and dirs."
    rlPhaseEnd

    rlJournalPrintText
rlJournalEnd
