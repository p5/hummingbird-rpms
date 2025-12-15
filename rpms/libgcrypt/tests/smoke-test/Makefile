# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Makefile of /CoreOS/libgcrypt/smoke-test
#   Description: Test calls upstream test suite.
#   Author: Ondrej Moris <omoris@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2010 Red Hat, Inc. All rights reserved.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

export TEST=/CoreOS/libgcrypt/smoke-test
export TESTVERSION=1.0

BUILT_FILES=

FILES=$(METADATA) runtest.sh Makefile PURPOSE

.PHONY: all install download clean

run: $(FILES) build
	./runtest.sh

build: $(BUILT_FILES)
	chmod a+x runtest.sh

clean:
	rm -f *~ $(BUILT_FILES)


include /usr/share/rhts/lib/rhts-make.include

$(METADATA): Makefile
	@echo "Owner:           Ondrej Moris <omoris@redhat.com>" > $(METADATA)
	@echo "Name:            $(TEST)" >> $(METADATA)
	@echo "TestVersion:     $(TESTVERSION)" >> $(METADATA)
	@echo "Path:            $(TEST_DIR)" >> $(METADATA)
	@echo "Description:     Test calls upstream test suite." >> $(METADATA)
	@echo "Type:            Sanity" >> $(METADATA)
	@echo "TestTime:        15m" >> $(METADATA)
	@echo "RunFor:          libgcrypt" >> $(METADATA)
	@echo "Requires:        libgcrypt" >> $(METADATA)
	@echo "Requires:        nfs-utils" >> $(METADATA)
	@echo "Requires:        rpm-build" >> $(METADATA)
	@echo "Requires:        autoconf automake libtool" >> $(METADATA)
	@echo "Requires:        gawk" >> $(METADATA)
	@echo "Requires:        gcc-c++" >> $(METADATA)
	@echo "Requires:        libgpg-error-devel" >> $(METADATA)
	@echo "Requires:        pkgconfig texinfo fipscheck libkcapi-fipscheck" >> $(METADATA)
	@echo "Requires:        crypto-policies-scripts" >> $(METADATA)
	@echo "Requires:        bc" >> $(METADATA)
	@echo "RhtsRequires:    library(distribution/fips)" >> $(METADATA)
	@echo "Releases:        -RHEL3 -RHEL4" >> $(METADATA)
	@echo "Priority:        Normal" >> $(METADATA)
	@echo "Architectures:   i386 x86_64 s390x ia64" >> $(METADATA)
	@echo "License:         GPLv2" >> $(METADATA)
	@echo "Confidential:    no" >> $(METADATA)
	@echo "Destructive:     no" >> $(METADATA)

	rhts-lint $(METADATA)
