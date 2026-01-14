#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-l2tp-sanity-test
#   Description: Test basic ip l2tp funcionality
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

    def link_exists(self, link):
        self.assertTrue(os.path.exists(os.path.join('/sys/class/net', link)))

    def add_veth(self):
        subprocess.check_output(['ip', 'link', 'add', 'veth-test', 'type', 'veth', 'peer', 'name', 'test-peer'])

    def del_veth(self):
        subprocess.check_output(['ip', 'link', 'del', 'veth-test'])

    def add_address(self, address, interface):
        subprocess.check_output(['ip', 'address', 'add', address, 'dev', interface])

class IPL2tpTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        self.add_veth()
        self.link_exists('veth-test')

        self.add_address('192.168.11.12/24', 'veth-test')
        self.add_address('192.168.11.13/24', 'test-peer')

    def tearDown(self):
        self.del_veth()

    def test_add_l2tp_add_tunnel(self):

        r = subprocess.call("ip l2tp add tunnel tunnel_id 3000 peer_tunnel_id 4000 encap udp local 192.168.11.12 remote 192.168.11.13 udp_sport 5000 udp_dport 6000", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'l2tp', 'show', 'tunnel', 'tunnel_id', '3000']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "From 192.168.11.12 to 192.168.11.13")
        self.assertRegex(output, "Peer tunnel 4000")
        self.assertRegex(output, "UDP source / dest ports: 5000/6000")

        r = subprocess.call("ip l2tp del tunnel tunnel_id 3000", shell=True)
        self.assertEqual(r, 0)

    def test_add_l2tp_add_tunnel_session(self):

        r = subprocess.call("ip l2tp add tunnel tunnel_id 3000 peer_tunnel_id 4000 encap udp local 192.168.11.12 remote 192.168.11.13 udp_sport 5000 udp_dport 6000", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'l2tp', 'show', 'tunnel', 'tunnel_id', '3000']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "From 192.168.11.12 to 192.168.11.13")
        self.assertRegex(output, "Peer tunnel 4000")
        self.assertRegex(output, "UDP source / dest ports: 5000/6000")

        r = subprocess.call(" ip l2tp add session tunnel_id 3000 session_id 1000 peer_session_id 2000", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'l2tp', 'show', 'session', 'tunnel_id', '3000', 'session_id' ,'1000']).rstrip().decode('utf-8')
        print(output)

        r = subprocess.call("ip l2tp del session tunnel_id 3000 session_id 1000", shell=True)
        self.assertEqual(r, 0)

        r = subprocess.call("ip l2tp del tunnel tunnel_id 3000", shell=True)
        self.assertEqual(r, 0)

    def test_setup_l2tp(self):

        r = subprocess.call("ip l2tp add tunnel tunnel_id 3000 peer_tunnel_id 4000 encap udp local 192.168.11.12 remote 192.168.11.13 udp_sport 5000 udp_dport 6000", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'l2tp', 'show', 'tunnel', 'tunnel_id', '3000']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "From 192.168.11.12 to 192.168.11.13")
        self.assertRegex(output, "Peer tunnel 4000")
        self.assertRegex(output, "UDP source / dest ports: 5000/6000")

        r = subprocess.call(" ip l2tp add session tunnel_id 3000 session_id 1000 peer_session_id 2000", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'l2tp', 'show', 'session', 'tunnel_id', '3000', 'session_id' ,'1000']).rstrip().decode('utf-8')
        print(output)

        r = subprocess.call("ip l2tp add tunnel tunnel_id 4000 peer_tunnel_id 3000 encap udp local 192.168.11.13 remote 192.168.11.12 udp_sport 6000 udp_dport 5000", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'l2tp', 'show', 'tunnel', 'tunnel_id', '3000']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "From 192.168.11.13 to 192.168.11.12")
        self.assertRegex(output, "Peer tunnel 4000")
        self.assertRegex(output, "UDP source / dest ports: 6000/5000")

        r = subprocess.call("ip l2tp add session tunnel_id 4000 session_id 2000 peer_session_id 1000", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'l2tp', 'show', 'session', 'tunnel_id', '4000', 'session_id' ,'2000']).rstrip().decode('utf-8')
        print(output)

        r = subprocess.call("ip link set l2tpeth0 up mtu 1488", shell=True)
        self.assertEqual(r, 0)
        r = subprocess.call("ip link set l2tpeth0 up mtu 1488", shell=True)
        self.assertEqual(r, 0)

        r = subprocess.call("ip addr add 10.42.1.1 peer 10.42.1.2 dev l2tpeth0", shell=True)
        self.assertEqual(r, 0)
        r = subprocess.call("ip addr add 10.42.1.2 peer 10.42.1.1 dev l2tpeth1", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'link', 'show']).rstrip().decode('utf-8')
        print(output)

        output=subprocess.check_output(['ping', '10.42.1.2','-c', '5']).rstrip().decode('utf-8')
        print(output)

        r = subprocess.call("ip l2tp del session tunnel_id 3000 session_id 1000", shell=True)
        self.assertEqual(r, 0)
        r = subprocess.call("ip l2tp del session tunnel_id 4000 session_id 2000", shell=True)
        self.assertEqual(r, 0)

        r = subprocess.call("ip l2tp del tunnel tunnel_id 3000", shell=True)
        self.assertEqual(r, 0)
        r = subprocess.call("ip l2tp del tunnel tunnel_id 4000", shell=True)
        self.assertEqual(r, 0)


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
