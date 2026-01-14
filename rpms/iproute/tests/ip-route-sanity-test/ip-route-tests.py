#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-route-sanity-test
#   Description: Test basic ip route funcionality
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
        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'up'])

    def del_dummy(self):
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

class IPRouteTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        self.add_dummy()

    def tearDown(self):
        self.del_dummy()

    def test_add_route(self):

        subprocess.check_output(['ip', 'route', 'add', '192.168.1.0/24', 'dev', 'dummy-test'])

        output=subprocess.check_output(['ip', 'route', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "192.168.1.0/24 dev dummy-test scope link")

        subprocess.check_output(['ip', 'route', 'delete', '192.168.1.0/24', 'dev', 'dummy-test'])

    def test_add_route_table(self):

        subprocess.check_output(['ip', 'route', 'add', 'table', '555', '192.168.1.0/24', 'dev', 'dummy-test'])

        output=subprocess.check_output(['ip', 'route', 'show', 'table', '555']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "192.168.1.0/24 dev dummy-test scope link")

        subprocess.check_output(['ip', 'route', 'delete', '192.168.1.0/24', 'dev', 'dummy-test', 'table', '555'])

    def test_add_blackhole(self):

        subprocess.check_output(['ip', 'route', 'add', 'blackhole', '192.168.1.0/24'])

        output=subprocess.check_output(['ip', 'route', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "blackhole 192.168.1.0/24")

        subprocess.check_output(['ip', 'route', 'delete', '192.168.1.0/24'])

    def test_add_unreachable(self):

        subprocess.check_output(['ip', 'route', 'add', 'unreachable', '192.168.1.0/24'])

        output=subprocess.check_output(['ip', 'route', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "unreachable 192.168.1.0/24")

        subprocess.check_output(['ip', 'route', 'delete', '192.168.1.0/24'])

    def test_add_prohibit(self):

        subprocess.check_output(['ip', 'route', 'add', 'prohibit', '192.168.1.0/24'])

        output=subprocess.check_output(['ip', 'route', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "prohibit 192.168.1.0/24")

        subprocess.check_output(['ip', 'route', 'delete', '192.168.1.0/24'])

    def test_add_throw(self):

        subprocess.check_output(['ip', 'route', 'add', 'throw', '192.168.1.0/24'])

        output=subprocess.check_output(['ip', 'route', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "throw 192.168.1.0/24")

        subprocess.check_output(['ip', 'route', 'delete', '192.168.1.0/24'])


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
