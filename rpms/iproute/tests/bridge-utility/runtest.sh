#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/iproute/Sanity/bridge-utility
#   Description: Test basic bridge funcionality
#   Author: David Spurek <dspurek@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2013 Red Hat, Inc. All rights reserved.
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

PACKAGES="$PACKAGE"
rlIsRHEL 6 && PACKAGES=( ${PACKAGES[@]} "bridge-utils" )
vxlan_name="testvxlan"
bridge_name="testbridge"
lsmod | grep dummy
dummy_loaded=$?

rlJournalStart
    rlPhaseStartSetup
        # Check reqiured packages.
        for P in ${PACKAGES[@]}; do rlCheckRpm $P || rlDie "Package $P is missing"; done

        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        no_dummy=0
        if [ $dummy_loaded -eq 1 ] ; then
                # dummy module doesn't loaded before the test
                modprobe dummy numdummies=2
        else
                # dummy module loaded before the test, backup number of loaded dummy devices (nmdumies parameter), it is doesn't show under /sys/module/dummy/parameters
                dummies_count=`ip a | grep dummy | tail -n 1 | sed -r 's/.*dummy([0-9]+).*/\1/'`
                if [ -z $dummies_count] ; then
                        # dummy module is loaded but no dummy device exists
                        no_dummy=1
                else
                        # get correct count, dummy0 is the first
                        let "dummies_count=$dummies_count+1"
                fi
                rmmod dummy
                modprobe dummy numdummies=2
        fi
        rlRun "ip addr flush dev dummy0"
        rlRun "ip link set dummy0 up"
        rlRun "ip addr flush dev dummy1"
        rlRun "ip link set dummy1 up"
        rlRun "ip addr add 127.0.0.13/24 dev dummy0" 0 "Setting IPv4 address to 
dummy0 interface"
        rlRun "ip addr add 127.0.0.14/24 dev dummy1" 0 "Setting IPv4 address to 
dummy1 interface"
    rlPhaseEnd

    rlPhaseStartTest "Test bridge fdb basic funcionality with vxlan device"
        rlRun "ip link add $vxlan_name type vxlan id 10 group 239.0.0.10 ttl 4 dev dummy0" 0 "add vxlan interface"
        rlRun "ip addr add 192.168.1.1/24 broadcast 192.168.1.255 dev $vxlan_name" 0 "setting address to vxlan interface"
        rlRun "ip -d link show $vxlan_name" 0 "show details about vxlan device" 

        vxlan_ether_address=`ip -d link show $vxlan_name | grep link/ether | awk '{print $2}'`
        echo "ethernet address of vxlan device is: $vxlan_ether_address"

        # add new entry to bridge fdb database (device must by type vxlan)
        rlRun "bridge fdb add $vxlan_ether_address dst 192.19.0.2 dev $vxlan_name"

        # check if entry was successfuly added
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertGrep "$vxlan_ether_address dst 192.19.0.2" bridge_show.out "-i"

        # try replace entry in bridge fdb database
        rlRun "bridge fdb replace $vxlan_ether_address dst 192.19.0.3 dev $vxlan_name"

        # check if entry was successfuly changed
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertGrep "$vxlan_ether_address dst 192.19.0.3" bridge_show.out "-i"

        rlRun "bridge fdb del $vxlan_ether_address dev $vxlan_name"

        # check if entry was successfuly deleted
        # 'default' entry added by ip link command should be still listed
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertNotGrep "$vxlan_ether_address dst 192.19.0.2" bridge_show.out "-i"
        rlAssertGrep "dst 239.0.0.10 via dummy0" bridge_show.out "-i"

        # add new entry to bridge fdb database with port,vni and via options
        rlRun "bridge fdb add $vxlan_ether_address dst 192.19.0.2 dev $vxlan_name port 10000 vni 100 via dummy0"
        # check if entry was successfuly added
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertGrep "$vxlan_ether_address dst 192.19.0.2 port 10000 vni 100 via dummy0" bridge_show.out "-i"

        rlRun "bridge fdb del $vxlan_ether_address dev $vxlan_name"

        # add new entry to bridge fdb database with self option
        rlRun "bridge fdb add $vxlan_ether_address dst 192.19.0.2 dev $vxlan_name self"
        # check if entry was successfuly added
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertGrep "$vxlan_ether_address dst 192.19.0.2 self" bridge_show.out "-i"

        # replace entry in bridge fdb database with temp option
        rlRun "bridge fdb replace $vxlan_ether_address dst 192.19.0.2 dev $vxlan_name temp"
        # check if entry was successfuly changed
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertGrep "$vxlan_ether_address dst 192.19.0.2 self static" bridge_show.out "-i"

        # replace entry in bridge fdb database with local option
        rlRun "bridge fdb replace $vxlan_ether_address dst 192.19.0.2 dev $vxlan_name local"
        # check if entry was successfuly changed
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertGrep "$vxlan_ether_address dst 192.19.0.2 self permanent" bridge_show.out "-i"

        # replace entry in bridge fdb database with router option
        rlRun "bridge fdb replace $vxlan_ether_address dst 192.19.0.2 dev $vxlan_name router"
        # check if entry was successfuly changed
        bridge fdb show dev $vxlan_name &> bridge_show.out
        cat bridge_show.out
        rlAssertGrep "$vxlan_ether_address dst 192.19.0.2 self router permanent" bridge_show.out "-i"

        rlRun "bridge fdb del $vxlan_ether_address dev $vxlan_name"
        rlRun "ip link del $vxlan_name" 0
    rlPhaseEnd

    rlPhaseStartTest "Test bridge fdb basic funcionality with bridge device, test bridge link set command"
        # on rhels < 7 must be bridge device added with brctl (add type bridge is not supported)
        rlIsRHEL '>=7' && rlRun "ip link add $bridge_name type bridge" 0 || rlRun "brctl addbr $bridge_name" 0

        if rlIsRHEL '>=7'; then
                rlRun "ip link set dummy0 master $bridge_name" 0 "Add dummy interface to bridge"
                rlRun "bridge link show dev dummy0"
                # test bridge link set, command is not supported on rhel < 7 (->ndo_bridge_setlink() is not in our kernel.)

                rlRun "bridge link set dev dummy0 cost 10"
                rlRun "bridge link show dev dummy0 &> bridge_show.out" 0
                cat bridge_show.out
                rlAssertGrep "dummy0.*cost 10 $" bridge_show.out "-i"

                # add new entry to bridge fdb database with self option
                rlRun "bridge fdb add 00:1b:21:55:23:61 dev dummy0 self"
                bridge fdb show dev dummy0 &> bridge_show.out
                cat bridge_show.out
                rlAssertGrep "00:1b:21:55:23:61 self" bridge_show.out "-i"
                # add new entry to bridge fdb database with master option
                rlRun "bridge fdb add 00:1b:21:55:23:62 dev dummy0 master"
                bridge fdb show dev dummy0 &> bridge_show.out
                cat bridge_show.out
                rlAssertGrep "00:1b:21:55:23:62 vlan 1" bridge_show.out "-i"

                # add new entry to bridge fdb database with master and self options (entries for both should be added)
                rlRun "bridge fdb add 00:1b:21:55:23:63 dev dummy0 self master"
                bridge fdb show dev dummy0 &> bridge_show.out
                cat bridge_show.out
                rlAssertGrep "00:1b:21:55:23:63 self" bridge_show.out "-i"
                rlAssertGrep "00:1b:21:55:23:63 vlan 1" bridge_show.out "-i"

        else
                rlRun "brctl addif $bridge_name dummy0" 0 "Add dummy interface to bridge"
                rlRun "brctl show $bridge_name"
        fi
        
        rlIsRHEL '>=7' && rlRun "ip link set dummy0 nomaster" 0 "Remove dummy vlan interface from bridge" || rlRun "brctl delif $bridge_name dummy0" 0 "Remove dummy interface from bridge"

        rlIsRHEL '>=7' && rlRun "ip link del $bridge_name" 0 || rlRun "brctl delbr $bridge_name" 0
    rlPhaseEnd

    rlPhaseStartTest "Test bridge vlan basic funcionality"
        # on rhels < 7 must be bridge device added with brctl (add type bridge is not supported)
        rlIsRHEL '>=7' && rlRun "ip link add $bridge_name type bridge" 0 || rlRun "brctl addbr $bridge_name" 0

        rlRun "ip link add link dummy0 name dummy0.10 type vlan id 10"
        if rlIsRHEL '>=7' ; then
                rlRun "ip link set dummy0.10 master $bridge_name" 0 "Add dummy vlan interface to bridge"
                rlRun "bridge link show dev dummy0.10"
        else
                rlRun "brctl addif $bridge_name dummy0.10" 0 "Add dummy vlan interface to bridge"
                rlRun "brctl show $bridge_name"
        fi
        # bridge vlan is not supported on rhel < 6.8
        if rlIsRHEL '>=7' || rlIsRHEL '>=6.8' || rlIsFedora; then
            rlRun "bridge vlan add dev dummy0.10 vid 5" 0
        else
            rlRun "bridge vlan add dev dummy0.10 vid 5" 2
        fi

        # test correct funcionality only on rhel 7
        if rlIsRHEL '>=7' ; then
                bridge vlan &> bridge_vlan.out
                cat bridge_vlan.out
                #rlAssertGrep "dummy0.10.*5" bridge_vlan.out "-i"
                #rlAssertGrep "dummy0.10.*10" bridge_vlan.out "-i"
                rlRun "grep -A 2 'dummy0.10' bridge_vlan.out | grep '5'"

                rlRun "bridge vlan del dev dummy0.10 vid 5"
                bridge vlan &> bridge_vlan.out
                cat bridge_vlan.out
                #rlAssertNotGrep "dummy0.10" bridge_vlan.out "-i"
                rlRun "grep -A 2 'dummy0.10' bridge_vlan.out | grep '5'" 1
        fi
        rlIsRHEL '>=7' && rlRun "ip link set dummy0.10 nomaster" 0 "Remove dummy vlan interface from bridge" || rlRun "brctl delif $bridge_name dummy0.10" 0 "Remove dummy vlan interface from bridge"

        rlRun "ip link del dev dummy0.10"

        rlIsRHEL '>=7' && rlRun "ip link del $bridge_name" 0 || rlRun "brctl delbr $bridge_name" 0
    rlPhaseEnd

    rlPhaseStartTest "Test bridge mdb basic funcionality"
        rlRun "bridge mdb show" 0
    rlPhaseEnd

    if rlIsRHEL '>=7'; then
        rlPhaseStartTest
            rlRun "ip link add test_bridge type bridge"
            rlRun "bridge fdb show | grep 'dev test_bridge' | grep 'master test_bridge'"
            rlRun "ip link del test_bridge"
        rlPhaseEnd
    fi

    rlPhaseStartCleanup
        rlRun "ip route flush dev dummy0"
        rlRun "ip link set dummy0 down"
        rlRun "ip addr flush dev dummy0"
        rlRun "ip route flush dev dummy1"
        rlRun "ip link set dummy1 down"
        rlRun "ip addr flush dev dummy1"
        if [ $dummy_loaded -eq 1 ] ; then
                rmmod dummy
        else
                rmmod dummy
                if [ $no_dummy -eq 1 ] ; then
                        # load dummy module and delete dummy0 with ip link
                        modprobe dummy
                         rlIsRHEL '>=7' && rlRun "ip link del dummy0"
                else
                        modprobe dummy numdummies=$dummies_count
                fi
        fi
        rlRun "service network restart" 0,1 "Restarting network, just for sure"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
