#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-address-sanity-test
#   Description: Test basic ip address funcionality
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

    def add_dummy(self):
        """ Setup """
        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])
        self.link_exists('dummy-test')

    def del_dummy(self):
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

class IPAddressTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        self.add_dummy()

    def tearDown(self):
        self.del_dummy()

    def test_add_address(self):

        r = subprocess.call("ip address add 192.168.1.200/24 dev dummy-test", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'address', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "192.168.1.200")

    def test_add_broadcast_address_label(self):

        r = subprocess.call("ip addr add 192.168.1.50/24 brd + dev dummy-test label dummy-test-Home", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'address', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "192.168.1.50")
        self.assertRegex(output, "192.168.1.255")
        self.assertRegex(output, "dummy-test-Home")

    def test_del_address(self):

        r = subprocess.call("ip address add 192.168.1.200/24 dev dummy-test", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'address', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "192.168.1.200")

        r = subprocess.call("ip address del 192.168.1.200/24 dev dummy-test", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'address', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertNotRegex(output, "192.168.1.200")

    def test_add_address_scope(self):

        r = subprocess.call("ip address add 192.168.1.200/24 dev dummy-test scope host", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'address', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "192.168.1.200")
        self.assertRegex(output, "host")

    def test_add_address_lifetime(self):

        r = subprocess.call("ip address add 192.168.1.200/24 dev dummy-test valid_lft 1000 preferred_lft 500", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'address', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "192.168.1.200")
        self.assertRegex(output, "1000sec")
        self.assertRegex(output, "500sec")

    def test_add_ipv6_address(self):

        r = subprocess.call("ip -6 addr add 2001:0db8:0:f101::1/64 dev dummy-test", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'address', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "2001:db8:0:f101::1")


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
