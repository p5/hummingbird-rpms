#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-link-sanity-test
#   Description: Test basic ip link funcionality
#
#   Author: Susant Sahani <susant@redhat.com>
#   Copyright (c) 2018 Red Hat, Inc.
# ~~~

import errno
import os
import sys
import time
import unittest
import subprocess
import signal
import shutil

def setUpModule():

    if shutil.which('ip') is None:
        raise OSError(errno.ENOENT, 'ip not found')

class IPLinkUtilities():

    def read_attr(self, link, attribute):
        """Read a link attributed from the sysfs."""

        with open(os.path.join('/sys/class/net', link, attribute)) as f:
            return f.readline().strip()

    def link_exists(self, link):

        self.assertTrue(os.path.exists(os.path.join('/sys/class/net', link)))

class IPLinkSetDevTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        """ Setup """
        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])
        self.link_exists('dummy-test')

    def tearDown(self):
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def test_set_dev_mtu(self):

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'mtu', '9000'])
        self.assertEqual('9000', self.read_attr('dummy-test', 'mtu'))

    def test_set_dev_up_down(self):

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'up'])
        output=subprocess.check_output(['ip', 'link', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, 'UP,LOWER_UP')

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'down'])
        output=subprocess.check_output(['ip', 'link', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertNotRegex(output, 'UP,LOWER_UP')

    def test_set_dev_address(self):

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'address', '02:01:02:03:04:08'])
        output=subprocess.check_output(['ip', 'link', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, 'link/ether 02:01:02:03:04:08')

    def test_set_dev_alias(self):

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'alias', 'test-test'])
        output=subprocess.check_output(['ip', 'link', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, 'test-test')

    def test_set_dev_name(self):

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'name', 'test-test'])
        output=subprocess.check_output(['ip', 'link', 'show', 'dev', 'test-test']).rstrip().decode('utf-8')
        self.assertRegex(output, 'test-test')

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'test-test', 'name', 'dummy-test'])

    def test_set_dev_multicast(self):

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'multicast', 'on'])
        output=subprocess.check_output(['ip', 'link', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, 'MULTICAST')

    def test_set_dev_all_multicast(self):

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'allmulticast', 'on'])
        output=subprocess.check_output(['ip', 'link', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, 'ALLMULTI')


class IPLinkKindTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        """ Setup """
        pass

    def tearDown(self):
        pass

    def test_add_veth_pair(self):

        subprocess.check_output(['ip', 'link', 'add', 'veth-test', 'type', 'veth', 'peer', 'name', 'veth-peer-test'])

        self.link_exists('veth-test')
        self.link_exists('veth-peer-test')

        subprocess.check_output(['ip', 'link', 'del', 'veth-test'])

    def test_add_dummy(self):

        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def test_add_vcan(self):

        subprocess.check_output(['ip', 'link', 'add', 'vcan-test', 'type', 'vcan'])

        self.link_exists('vcan-test')

        subprocess.check_output(['ip', 'link', 'del', 'vcan-test'])

    def test_add_vxcan(self):

        subprocess.check_output(['ip', 'link', 'add', 'vxcan-test', 'type', 'vxcan'])

        self.link_exists('vxcan-test')

        subprocess.check_output(['ip', 'link', 'del', 'vxcan-test'])

    def test_add_vlan(self):

        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'name', 'vlantest.100', 'type', 'vlan', 'id', '100'])

        self.link_exists('vlantest.100')

        subprocess.check_output(['ip', 'link', 'del', 'vlantest.100'])
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def test_add_macvlan(self):

        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'macvlan-test', 'type', 'macvlan', 'mode', 'bridge'])

        self.link_exists('macvlan-test')

        subprocess.check_output(['ip', 'link', 'del', 'macvlan-test'])
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def test_add_macvtap(self):

        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'macvtap-test', 'type', 'macvtap', 'mode', 'bridge'])

        self.link_exists('macvtap-test')

        subprocess.check_output(['ip', 'link', 'del', 'macvtap-test'])
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def test_add_bridge(self):

        subprocess.check_output(['ip', 'link', 'add', 'bridge-test', 'type', 'bridge'])

        self.link_exists('bridge-test')

        subprocess.check_output(['ip', 'link', 'del', 'bridge-test'])

    def test_add_bond(self):

        subprocess.check_output(['ip', 'link', 'add', 'bond-test', 'type', 'bond'])

        self.link_exists('bond-test')

        subprocess.check_output(['ip', 'link', 'del', 'bond-test'])

    def test_add_team(self):

        subprocess.check_output(['ip', 'link', 'add', 'team-test', 'type', 'team'])

        self.link_exists('team-test')

        subprocess.check_output(['ip', 'link', 'del', 'team-test'])

    def test_add_ipip_tunnel(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'test-ipiptun', 'mode', 'ipip', 'remote', '10.3.3.3', 'local', '10.4.4.4', 'ttl' ,'64'])

        self.link_exists('test-ipiptun')

        subprocess.check_output(['ip', 'link', 'del', 'test-ipiptun'])

    def test_add_gre_tunnel(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'test-gretun', 'mode', 'gre', 'remote', '10.3.3.3', 'local', '10.4.4.4', 'ttl' ,'64'])

        self.link_exists('test-gretun')

        subprocess.check_output(['ip', 'link', 'del', 'test-gretun'])

    def test_add_gretap_tunnel(self):

        subprocess.check_output(['ip', 'link', 'add', 'test-gretap', 'type', 'gretap', 'remote', '10.3.3.3', 'local', '10.4.4.4'])

        self.link_exists('test-gretap')

        subprocess.check_output(['ip', 'link', 'del', 'test-gretap'])

    def test_add_ip6gre_tunnel(self):

        subprocess.check_output(['ip', 'link', 'add', 'test-ip6gre', 'type', 'ip6gre', 'remote', '2a00:ffde:4567:edde::4987', 'local', '2001:473:fece:cafe::5179'])

        self.link_exists('test-ip6gre')

        subprocess.check_output(['ip', 'link', 'del', 'test-ip6gre'])

    def test_add_ip6gretap_tunnel(self):

        subprocess.check_output(['ip', 'link', 'add', 'test-ip6gretap', 'type', 'ip6gretap', 'remote', '2a00:ffde:4567:edde::4987', 'local', '2001:473:fece:cafe::5179'])

        self.link_exists('test-ip6gretap')

        subprocess.check_output(['ip', 'link', 'del', 'test-ip6gretap'])

    def test_add_erspan_tunnel(self):

        subprocess.check_output(['ip', 'link', 'add', 'dev', 'test-erspan', 'type', 'erspan', 'seq', 'key', '100','erspan', '123', 'remote', '10.3.3.3', 'local', '10.4.4.4'])

        self.link_exists('test-erspan')

        subprocess.check_output(['ip', 'link', 'del', 'test-erspan'])

    def test_add_ip6erspan_tunnel(self):

        subprocess.check_output(['ip', 'link', 'add', 'dev', 'test-ip6erspan', 'type', 'erspan', 'seq', 'key', '101','erspan', '1234', 'remote', '10.3.3.3', 'local', '10.4.4.4'])

        self.link_exists('test-ip6erspan')

        subprocess.check_output(['ip', 'link', 'del', 'test-ip6erspan'])

    def test_add_sit_tunnel(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'test-sittun', 'mode', 'sit', 'remote', '10.3.3.3', 'local', '10.4.4.4', 'ttl' ,'64'])

        self.link_exists('test-sittun')

        subprocess.check_output(['ip', 'link', 'del', 'test-sittun'])

    def test_add_vti_tunnel(self):

        subprocess.check_output(['ip', 'link', 'add', 'dev', 'test-vtitun', 'type', 'vti', 'remote', '10.3.3.3', 'local', '10.4.4.4'])

        self.link_exists('test-vtitun')

        subprocess.check_output(['ip', 'link', 'del', 'test-vtitun'])

    def test_add_geneve_tunnel(self):

        subprocess.check_output(['ip', 'link', 'add', 'dev', 'test-geneve-tun', 'type', 'geneve', 'remote', '10.3.3.3', 'vni', '1234'])

        self.link_exists('test-geneve-tun')

        subprocess.check_output(['ip', 'link', 'del', 'test-geneve-tun'])

    def test_add_ipvlan(self):

        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'name', 'test-ipvlan', 'type', 'ipvlan'])
        self.link_exists('test-ipvlan')
        subprocess.check_output(['ip', 'link', 'del', 'test-ipvlan'])

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'name', 'test-ipvlan', 'type', 'ipvlan','mode', 'l2', 'bridge'])
        self.link_exists('test-ipvlan')
        subprocess.check_output(['ip', 'link', 'del', 'test-ipvlan'])

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'name', 'test-ipvlan', 'type', 'ipvlan','mode', 'l2', 'private'])
        self.link_exists('test-ipvlan')
        subprocess.check_output(['ip', 'link', 'del', 'test-ipvlan'])

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'name', 'test-ipvlan', 'type', 'ipvlan','mode', 'l2', 'vepa'])
        self.link_exists('test-ipvlan')
        subprocess.check_output(['ip', 'link', 'del', 'test-ipvlan'])

        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def test_add_vxlan(self):

        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'link', 'add', 'vxlan-test', 'type', 'vxlan', 'id', '42', 'group', '239.1.1.1', 'dev', 'dummy-test' ,'dstport', '4789'])
        self.link_exists('vxlan-test')

        subprocess.check_output(['ip', 'link', 'del', 'vxlan-test'])
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def test_add_vrf(self):

        subprocess.check_output(['ip', 'link', 'add', 'vrf-test', 'type', 'vrf', 'table', '10'])

        self.link_exists('vrf-test')

        subprocess.check_output(['ip', 'link', 'del', 'vrf-test'])

    def test_add_macsec(self):
        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'link', 'add', 'link', 'dummy-test', 'test-macsec', 'type', 'macsec'])

        self.link_exists('test-macsec')

        subprocess.check_output(['ip', 'macsec', 'add', 'test-macsec', 'tx', 'sa', '0', 'pn', '1', 'on', 'key', '02', '09876543210987654321098765432109'])
        subprocess.check_output(['ip', 'macsec', 'add', 'test-macsec', 'rx', 'address', '56:68:a5:c2:4c:14', 'port', '1'])
        subprocess.check_output(['ip', 'macsec', 'add', 'test-macsec', 'rx', 'address', '56:68:a5:c2:4c:14', 'port', '1', 'sa', '0', 'pn', '1', 'on', 'key', '01', '12345678901234567890123456789012'])

        subprocess.check_output(['ip', 'link', 'del', 'test-macsec'])
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
