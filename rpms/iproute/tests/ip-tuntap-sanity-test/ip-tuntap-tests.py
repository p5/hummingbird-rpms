#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-tuntap-sanity-test
#   Description: Test basic ip tuntap funcionality
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

class IPTuntapTests(unittest.TestCase, IPLinkUtilities):

    def test_add_tap(self):

        subprocess.check_output(['ip', 'tuntap', 'add', 'name', 'tap-test', 'mode', 'tap'])
        self.link_exists('tap-test')

        output=subprocess.check_output(['ip', 'tuntap', 'show', 'dev', 'tap-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "tap-test: tap")

        subprocess.check_output(['ip', 'link', 'del', 'tap-test'])

    def test_add_tun(self):

        subprocess.check_output(['ip', 'tuntap', 'add', 'name', 'tun-test', 'mode', 'tun'])
        self.link_exists('tun-test')

        output=subprocess.check_output(['ip', 'tuntap', 'show', 'dev', 'tun-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "tun-test: tun")

        subprocess.check_output(['ip', 'link', 'del', 'tun-test'])

    def test_add_tun_user_group(self):

        subprocess.check_output(['ip', 'tuntap', 'add', 'name', 'tun-test', 'mode', 'tun', 'user', 'root', 'group', 'root'])
        self.link_exists('tun-test')

        output=subprocess.check_output(['ip', 'tuntap', 'show', 'dev', 'tun-test']).rstrip().decode('utf-8')
        self.assertRegex(output, "tun-test: tun")
        self.assertRegex(output, "user 0 group 0")

        subprocess.check_output(['ip', 'link', 'del', 'tun-test'])

if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
