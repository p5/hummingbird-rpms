#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-fou-sanity-test
#   Description: Test basic ip fou funcionality
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

class IPFOUTests(unittest.TestCase):

    def test_configure_fou_receive_port_gre(self):
        ''' Configure a FOU receive port for GRE bound to 7777'''

        subprocess.call(" ip fou add port 7777 ipproto 47", shell=True)
        output=subprocess.check_output(['ip', 'fou', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "port 7777 ipproto 47")

        subprocess.call("ip fou del port 7777", shell=True)

    def test_configure_fou_receive_port_ipip(self):
        ''' Configure a FOU receive port for IPIP bound to 8888'''

        subprocess.call("ip fou add port 8888 ipproto 4", shell=True)
        output=subprocess.check_output(['ip', 'fou', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "port 8888 ipproto 4")

        subprocess.call("ip fou del port 8888", shell=True)

    def test_configure_fou_receive_port_gue(self):
        ''' Configure a GUE receive port bound to 9999 '''

        subprocess.call("ip fou add port 9999 gue", shell=True)
        output=subprocess.check_output(['ip', 'fou', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "port 9999 gue")

        subprocess.call("ip fou del port 9999", shell=True)

    def test_configure_fou_with_ipip(self):
        ''' IP over UDP tunnel '''

        subprocess.call("ip fou add port 9000 ipproto 4", shell=True)
        output=subprocess.check_output(['ip', 'fou', 'show']).rstrip().decode('utf-8')
        print(output)
        self.assertRegex(output, "port 9000 ipproto 4")

        subprocess.call("ip link add name tunudp type ipip remote 192.168.2.2 local 192.168.2.1 ttl 225 encap fou encap-sport auto encap-dport 9000", shell=True)
        output=subprocess.check_output(['ip', '-d', 'link', 'show', 'tunudp']).rstrip().decode('utf-8')
        self.assertRegex(output, "encap fou")

        subprocess.call("ip link del tunudp", shell=True)
        subprocess.call("ip fou del port 9000", shell=True)

if __name__ == '__main__':
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout,
                                                     verbosity=2))
