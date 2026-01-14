#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-neighbour-sanity-test
#   Description: Test basic ip neighbour funcionality
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

        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])
        self.link_exists('dummy-test')

    def del_dummy(self):

        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

class IPNeighborTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        self.add_dummy()
        self.link_exists('dummy-test')

    def tearDown(self):
        self.del_dummy()

    def test_add_neighbor(self):

        subprocess.call("ip neighbor add 192.168.100.1 lladdr 00:c0:7b:7d:00:c8 dev dummy-test nud permanent", shell=True)
        output=subprocess.check_output(['ip', 'neighbour', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "192.168.100.1 lladdr 00:c0:7b:7d:00:c8 PERMANENT")

        subprocess.call("ip neighbor del 192.168.100.1 dev dummy-test", shell=True)

    def test_replace_neighbor(self):

        subprocess.call("ip neighbor add 192.168.99.254 lladdr 00:80:c8:27:69:2d dev dummy-test", shell=True)
        output=subprocess.check_output(['ip', 'neighbour', 'show', 'dev', 'dummy-test']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "192.168.99.254 lladdr 00:80:c8:27:69:2d PERMANENT")

        subprocess.call("ip neighbor change 192.168.99.254 lladdr 00:80:c8:27:69:2d dev dummy-test", shell=True)
        print(output)
        self.assertRegex(output, "192.168.99.254 lladdr 00:80:c8:27:69:2d PERMANENT")

        subprocess.call("ip neighbor del 192.168.99.254 dev dummy-test", shell=True)


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
