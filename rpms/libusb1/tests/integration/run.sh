#!/bin/sh

set -e

ldd /usr/bin/libusb-test-stress
/usr/bin/libusb-test-stress
/usr/bin/libusb-test-umockdev
/usr/bin/libusb-test-libusb
/usr/bin/libusb-example-listdevs
