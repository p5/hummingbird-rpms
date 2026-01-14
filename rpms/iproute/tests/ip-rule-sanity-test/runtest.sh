#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/iproute/Sanity/ip-rule-sanity-test
#   Description: Test basic ip rule funcionality
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
DEFAULT_IFACE="$(ip route show | grep default | sed 's/.*dev \([^ ]\+\) .*/\1/' | head -n 1)"
rlIsRHEL '>=7' && IP_RULE_MANPAGE="ip-rule" || IP_RULE_MANPAGE="ip"


rlJournalStart
    rlPhaseStartSetup
        rlCheckRpm "$PACKAGE"
    rlPhaseEnd

    rlPhaseStartTest "Basic sanity test"
        rlRun "ip rule list"

        rlRun "ip rule add from 172.29.0.0/24 to 172.29.1.0/24 table 1110"
        rlRun "ip rule add not from 172.29.0.0/24 to 172.29.1.0/24 table 1111"
        rlRun "ip -6 rule add from 2404:6800:4003:801::1015/32 to 2404:6800:4003:801::1014/32 table 1111"
        rlIsRHEL '>=7' && rlRun "ip rule add oif ${DEFAULT_IFACE} table 1111"
        rlRun "ip rule add iif ${DEFAULT_IFACE} tos 10 table 1112"
        rlRun "ip rule add fwmark 123 pref 100 table 1112"
        rlRun "ip rule add not fwmark 124 pref 101 unreachable"
        rlRun "ip rule add fwmark 125 pref 102 prohibit"
        rlRun "ip rule add fwmark 126 pref 103 unicast"
        rlRun "ip rule add from 172.29.2.0/24 tos 10 blackhole"
        rlRun "ip rule add from 172.29.0.0/24 tos 6 prio 99 goto 103"

        rlRun "ip rule list"

        rlRun "ip rule list | grep 'from 172.29.0.0/24 to 172.29.1.0/24'"
        rlRun "ip rule list | grep 'not from 172.29.0.0/24 to 172.29.1.0/24'"
        rlRun "ip -6 rule list | grep 'from 2404:6800:4003:801::1015/32 to 2404:6800:4003:801::1014/32'"
        rlIsRHEL '>=7' && rlRun "ip rule list | grep 'oif ${DEFAULT_IFACE}'"
        ! rlIsFedora && rlRun "ip rule list | grep 'tos lowdelay iif ${DEFAULT_IFACE}'"
        rlRun "ip rule list | grep 'from all fwmark 0x7b'"
        rlRun "ip rule list | grep 'not from all fwmark 0x7c unreachable'"
        rlRun "ip rule list | grep 'from all fwmark 0x7d prohibit'"
        rlRun "ip rule list | grep 'from all fwmark 0x7e'"
        ! rlIsFedora && rlRun "ip rule list | grep 'from 172.29.2.0/24 tos lowdelay blackhole'"
        rlRun "ip rule list | grep 'from 172.29.0.0/24 tos 0x06 goto 103'"

        rlRun "ip rule list"

        rlRun "ip rule del from 172.29.0.0/24 to 172.29.1.0/24"
        rlRun "ip rule del not from 172.29.0.0/24 to 172.29.1.0/24"
        rlRun "ip -6 rule del from 2404:6800:4003:801::1015/32 to 2404:6800:4003:801::1014/32"
        rlIsRHEL '>=7' && rlRun "ip rule del oif ${DEFAULT_IFACE}"
        ! rlIsFedora && rlRun "ip rule del iif ${DEFAULT_IFACE} tos lowdelay"
        rlRun "ip rule del fwmark 123 pref 100"
        rlRun "ip rule del not fwmark 124 pref 101 unreachable"
        rlRun "ip rule del fwmark 125 pref 102 prohibit"
        rlRun "ip rule del fwmark 126 pref 103 unicast"
        rlRun "ip rule del from 172.29.2.0/24 tos 10 blackhole"
        rlRun "ip rule del from 172.29.0.0/24 tos 6 prio 99 goto 103"

        rlRun "ip rule list"
    rlPhaseEnd

    if rlIsRHEL '>=7'; then
        rlPhaseStartTest
            saved_rule=$(ip rule list | grep '^0' | cut -d : -f 2 | head -n 1)
            rlRun "ip rule del prio 0" 0 "Removing rule with prio 0."
            rlRun "ip rule add prio 0 ${saved_rule}" 0 "Re-creating rule with prio 0."
            rlRun "man ${IP_RULE_MANPAGE} | col -b | grep 'Rule 0 is special. It cannot be deleted or overridden.'" 1
        rlPhaseEnd
    fi

    rlPhaseStartTest
        rlRun "man ${IP_RULE_MANPAGE} | col -b | grep 'reject'" 1
        rlRun "ip rule help 2>&1 | grep 'reject'" 1
    rlPhaseEnd

    rlPhaseStartCleanup
    rlPhaseEnd

    rlJournalPrintText
rlJournalEnd
