#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-tunnel-sanity-test
#   Description: Test basic ip tunnel funcionality
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

    def add_dummy(self):
        subprocess.check_output(['ip', 'link', 'add', 'dummy-test', 'type', 'dummy'])
        self.link_exists('dummy-test')

    def del_dummy(self):
        subprocess.check_output(['ip', 'link', 'del', 'dummy-test'])

    def link_exists(self, link):
        self.assertTrue(os.path.exists(os.path.join('/sys/class/net', link)))

class IPTunnelTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        self.add_dummy()
        self.link_exists('dummy-test')

    def tearDown(self):
        self.del_dummy()

    def test_add_ipip(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'ipiptun-test', 'mode', 'ipip', 'local', '10.3.3.3', 'remote', '10.4.4.4', 'ttl', '64', 'dev', 'dummy-test'])
        self.link_exists('ipiptun-test')

        output=subprocess.check_output(['ip', 'tunnel']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "ipiptun-test: ip/ip remote 10.4.4.4 local 10.3.3.3 dev dummy-test ttl 64")

        subprocess.check_output(['ip', 'link', 'del', 'ipiptun-test'])

    def test_add_gre(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'gretun-test', 'mode', 'gre', 'local', '10.3.3.3', 'remote', '10.4.4.4', 'ttl', '64', 'dev', 'dummy-test'])
        self.link_exists('gretun-test')

        output=subprocess.check_output(['ip', 'tunnel']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "gretun-test: gre/ip remote 10.4.4.4 local 10.3.3.3 dev dummy-test ttl 64")

        subprocess.check_output(['ip', 'link', 'del', 'gretun-test'])

    def test_add_sit(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'sittun-test', 'mode', 'sit', 'local', '10.3.3.3', 'remote', '10.4.4.4', 'ttl', '64', 'dev', 'dummy-test'])
        self.link_exists('sittun-test')

        output=subprocess.check_output(['ip', 'tunnel']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "sittun-test: ipv6/ip remote 10.4.4.4 local 10.3.3.3 dev dummy-test ttl 64")

        subprocess.check_output(['ip', 'link', 'del', 'sittun-test'])

    def test_add_isatap(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'isatap-test', 'mode', 'sit', 'local', '10.3.3.3', 'remote', '10.4.4.4', 'ttl', '64', 'dev', 'dummy-test'])
        self.link_exists('isatap-test')

        output=subprocess.check_output(['ip', 'tunnel']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "isatap-test: ipv6/ip remote 10.4.4.4 local 10.3.3.3 dev dummy-test ttl 64")

        subprocess.check_output(['ip', 'link', 'del', 'isatap-test'])

    def test_add_vti(self):

        subprocess.check_output(['ip', 'tunnel', 'add', 'vti-test', 'mode', 'sit', 'local', '10.3.3.3', 'remote', '10.4.4.4', 'ttl', '64', 'dev', 'dummy-test'])
        self.link_exists('vti-test')

        output=subprocess.check_output(['ip', 'tunnel']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "vti-test: ipv6/ip remote 10.4.4.4 local 10.3.3.3 dev dummy-test ttl 64")

        subprocess.check_output(['ip', 'link', 'del', 'vti-test'])


if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
