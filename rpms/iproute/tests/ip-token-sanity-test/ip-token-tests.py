#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-token-sanity-test
#   Description: Test basic ip token funcionality
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

class IPTokenTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        self.add_veth()
        self.link_exists('veth-test')

    def tearDown(self):
        self.del_veth()

    def test_add_token(self):

        r = subprocess.call("ip token set ::1a:2b:3c:4d/64 dev veth-test", shell=True)
        self.assertEqual(r, 0)

        output=subprocess.check_output(['ip', 'token', 'get', 'dev', 'veth-test']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "token ::1a:2b:3c:4d dev veth-test")

        r = subprocess.call("ip token del ::1a:2b:3c:4d/64 dev veth-test", shell=True)
        self.assertEqual(r, 0)

if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
