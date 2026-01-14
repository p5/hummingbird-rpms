#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-address-label-sanity-test
#   Description: Test basic ip addrlabel funcionality
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

class IPAddressLabelTests(unittest.TestCase, IPLinkUtilities):

    def setUp(self):
        self.add_dummy()
        self.link_exists('dummy-test')

    def tearDown(self):
        self.del_dummy()

    def test_add_address_label(self):

        subprocess.call("ip addrlabel add prefix 2001:6f8:12d8:2::/64 label 200", shell=True)
        subprocess.call("ip addrlabel add prefix 2001:6f8:900:8cbc::/64 label 300", shell=True)
        subprocess.call("ip addrlabel add prefix 2001:4dd0:ff00:834::/64 label 200", shell=True)
        subprocess.call("ip addrlabel add prefix 2a01:238:423d:8800::/64 label 300", shell=True)

        output=subprocess.check_output(['ip', 'addrlabel']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "prefix 2001:6f8:12d8:2::/64 label 200")
        self.assertRegex(output, "prefix 2001:6f8:900:8cbc::/64 label 300")
        self.assertRegex(output, "prefix 2001:4dd0:ff00:834::/64 label 200")
        self.assertRegex(output, "prefix 2a01:238:423d:8800::/64 label 300")

        subprocess.call("ip addrlabel del prefix 2001:6f8:12d8:2::/64 label 200", shell=True)
        subprocess.call("ip addrlabel del prefix 2001:6f8:900:8cbc::/64 label 300", shell=True)
        subprocess.call("ip addrlabel del prefix 2001:4dd0:ff00:834::/64 label 200", shell=True)
        subprocess.call("ip addrlabel del prefix 2a01:238:423d:8800::/64 label 300", shell=True)

    def test_add_address_label_dev(self):

        subprocess.call("ip addrlabel add prefix 2001:6f8:12d8:2::/64 label 200 dev dummy-test", shell=True)
        subprocess.call("ip addrlabel add prefix 2001:6f8:900:8cbc::/64 label 300 dev dummy-test", shell=True)
        subprocess.call("ip addrlabel add prefix 2001:4dd0:ff00:834::/64 label 200 dev dummy-test", shell=True)
        subprocess.call("ip addrlabel add prefix 2a01:238:423d:8800::/64 label 300 dev dummy-test", shell=True)

        output=subprocess.check_output(['ip', 'addrlabel']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "prefix 2001:6f8:12d8:2::/64 dev dummy-test label 200")
        self.assertRegex(output, "prefix 2001:6f8:900:8cbc::/64 dev dummy-test label 300")
        self.assertRegex(output, "prefix 2001:4dd0:ff00:834::/64 dev dummy-test label 200")
        self.assertRegex(output, "prefix 2a01:238:423d:8800::/64 dev dummy-test label 300")

        subprocess.call("ip addrlabel del prefix 2001:6f8:12d8:2::/64 label 200 dev dummy-test", shell=True)
        subprocess.call("ip addrlabel del prefix 2001:6f8:900:8cbc::/64 label 300 dev dummy-test", shell=True)
        subprocess.call("ip addrlabel del prefix 2001:4dd0:ff00:834::/64 label 200 dev dummy-test", shell=True)
        subprocess.call("ip addrlabel del prefix 2a01:238:423d:8800::/64 label 300 dev dummy-test", shell=True)

if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
