# Makefile - diff-hang-long-files
# Author: Michal Fabry <mfabry@redhat.com>
# Location: /CoreOS/diffutils/Regression/diff-hang-long-files/Makefile

# Description: Diff appears to hang in long file

# Copyright (c) 2009 Red Hat, Inc. All rights reserved. This copyrighted material
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.



TOPLEVEL_NAMESPACE=/CoreOS
PACKAGE_NAME=diffutils
RELATIVE_PATH=Regression/diff-hang-long-files

export TEST=$(TOPLEVEL_NAMESPACE)/$(PACKAGE_NAME)/$(RELATIVE_PATH)
export TESTVERSION=1.0

BUILT_FILES=

FILES=$(METADATA) runtest.sh Makefile

.PHONY: all install download clean

run: $(FILES) build
	./runtest.sh

build: $(BUILT_FILES)
	chmod a+x ./runtest.sh

clean:
	rm -f *~ $(BUILT_FILES)


include /usr/share/rhts/lib/rhts-make.include


$(METADATA): Makefile
	@touch $(METADATA)
	@echo "Owner:        Michal Fabry <mfabry@redhat.com>" > $(METADATA)
	@echo "Name:         $(TEST)" >> $(METADATA)
	@echo "Path:         $(TEST_DIR)"       >> $(METADATA)
	@echo "TestVersion:  $(TESTVERSION)"    >> $(METADATA)
	@echo "Description:  Diff appears to hang in long file" >> $(METADATA)
	@echo "Type:         Regression" >> $(METADATA)
	@echo "TestTime:     5m" >> $(METADATA)
	@echo "RunFor:       $(PACKAGE_NAME)" >> $(METADATA)
	@echo "Requires:     $(PACKAGE_NAME) words time" >> $(METADATA)
	@echo "License:      GPLv2" >> $(METADATA)

	rhts-lint $(METADATA)
