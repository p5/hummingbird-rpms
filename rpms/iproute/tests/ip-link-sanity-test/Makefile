#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1+
# ~~~
#   runtest.sh of /CoreOS/iproute/Sanity/ip-link-sanity-test
#   Description: Test basic ip link funcionality
#
#   Author: Susant Sahani <susant@redhat.com>
#   Copyright (c) 2018 Red Hat, Inc.
#~~~

export TEST=/CoreOS/iproute/Sanity/ip-link-sanity-test
export TESTVERSION=1.0

BUILT_FILES=

FILES=$(METADATA) runtest.sh Makefile PURPOSE

.PHONY: all install download clean

run: $(FILES) build
	./runtest.sh

build: $(BUILT_FILES)
	test -x runtest.sh || chmod a+x runtest.sh

clean:
	rm -f *~ $(BUILT_FILES)


include /usr/share/rhts/lib/rhts-make.include

$(METADATA): Makefile
	@echo "Owner:           Susant Sahani <susant@redhat.com>" > $(METADATA)
	@echo "Name:            $(TEST)" >> $(METADATA)
	@echo "TestVersion:     $(TESTVERSION)" >> $(METADATA)
	@echo "Path:            $(TEST_DIR)" >> $(METADATA)
	@echo "Description:     Test basic ip link funcionality" >> $(METADATA)
	@echo "Type:            Sanity" >> $(METADATA)
	@echo "TestTime:        15m" >> $(METADATA)
	@echo "RunFor:          iproute" >> $(METADATA)
	@echo "Requires:        iproute" >> $(METADATA)
	@echo "Priority:        Normal" >> $(METADATA)
	@echo "License:         GPLv2" >> $(METADATA)
	@echo "Confidential:    no" >> $(METADATA)
	@echo "Destructive:     no" >> $(METADATA)

	rhts-lint $(METADATA)
