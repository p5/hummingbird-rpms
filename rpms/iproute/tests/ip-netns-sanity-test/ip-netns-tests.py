#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-netns-sanity-test
#   Description: Test basic ip netns funcionality
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

class GenericUtilities():

    def path_exists(self, path):
        self.assertTrue(os.path.exists(os.path.join('/var/run/netns', path)))

    def link_exists(self, link):
        self.assertTrue(os.path.exists(os.path.join('/sys/class/net', link)))

    def add_veth(self):
        subprocess.check_output(['ip', 'link', 'add', 'veth-test', 'type', 'veth', 'peer', 'name', 'test-peer'])

    def del_veth(self):
        subprocess.check_output(['ip', 'link', 'del', 'veth-test'])

    def add_dummy(self):
        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])

    def del_dummy(self):
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

class IPNsTests(unittest.TestCase, GenericUtilities):

    def test_add_ns(self):

        subprocess.check_output(['ip', 'netns', 'add', 'net-ns-test'])
        self.path_exists('net-ns-test')

        output=subprocess.check_output(['ip', 'netns', 'list']).rstrip().decode('utf-8')
        self.assertRegex(output, "net-ns-test")

        self.addCleanup(subprocess.call, ['ip', 'netns', 'del', 'net-ns-test'])

    def test_add_dummy_interface_to_ns(self):

        self.add_dummy()
        self.link_exists('dummy-test')

        subprocess.check_output(['ip', 'netns', 'add', 'net-ns-test'])
        self.path_exists('net-ns-test')

        output=subprocess.check_output(['ip', 'netns', 'list']).rstrip().decode('utf-8')
        self.assertRegex(output, "net-ns-test")

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'dummy-test', 'netns', 'net-ns-test'])

        output=subprocess.check_output(['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'link', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "dummy-test")

        self.addCleanup(subprocess.call, ['ip', 'netns', 'del', 'net-ns-test'])
        self.addCleanup(subprocess.call, ['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'link', 'del', 'dummy-test'])

    def test_add_veth_interface_to_ns(self):

        self.add_veth()
        self.link_exists('veth-test')

        subprocess.check_output(['ip', 'netns', 'add', 'net-ns-test'])
        self.path_exists('net-ns-test')

        output=subprocess.check_output(['ip', 'netns', 'list']).rstrip().decode('utf-8')
        self.assertRegex(output, "net-ns-test")

        subprocess.check_output(['ip', 'link', 'set', 'dev', 'test-peer', 'netns', 'net-ns-test'])

        output=subprocess.check_output(['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'link', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "test-peer")

        # Setup IP address of veth-test.
        subprocess.check_output(['ip', 'addr', 'add', '10.200.1.1/24', 'dev', 'veth-test'])
        subprocess.check_output(['ip', 'link', 'set', 'veth-test', 'up'])

        # Setup IP address of v-peer1.
        subprocess.check_output(['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'addr', 'add',' 10.200.1.2/24', 'dev', 'test-peer'])
        subprocess.check_output(['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'link', 'set', 'test-peer', 'up'])
        subprocess.check_output(['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'link', 'set', 'lo', 'up'])

        output=subprocess.check_output(['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'addr', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "test-peer")
        self.assertRegex(output, "lo: <LOOPBACK,UP,LOWER_UP>")
        self.assertRegex(output, "inet 10.200.1.2/24")

        output=subprocess.check_output(['ip', 'netns', 'exec', 'net-ns-test', 'ping', '10.200.1.1', '-c', '5']).rstrip().decode('utf-8')
        print(output)

        self.addCleanup(subprocess.call, ['ip', 'netns', 'del', 'net-ns-test'])
        self.addCleanup(subprocess.call, ['ip', 'netns', 'exec', 'net-ns-test', 'ip', 'link', 'del', 'test-peer'])


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
