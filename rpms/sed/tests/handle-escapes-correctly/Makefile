# The toplevel namespace within which the test lives.
TOPLEVEL_NAMESPACE=/CoreOS

# The name of the package under test:
PACKAGE_NAME=sed

# The path of the test below the package:
RELATIVE_PATH=handle-escapes-correctly

# Version of the Test. Used with make tag.
export TESTVERSION=1.1

# The compiled namespace of the test.
export TEST=$(TOPLEVEL_NAMESPACE)/$(PACKAGE_NAME)/$(RELATIVE_PATH)

.PHONY: all install download clean

BUILT_FILES= # executables to be built should be added here, they will be generated on the system under test.
FILES=$(METADATA) runtest.sh Makefile handle-escapes-correctly.sh

run: $(FILES) build
	./runtest.sh

build: $(BUILT_FILES)
	chmod a+x ./runtest.sh
	chmod a+x ./handle-escapes-correctly.sh

clean:
	rm -f *~ $(BUILT_FILES)

# Include Common Makefile
include /usr/share/rhts/lib/rhts-make.include

# Generate the testinfo.desc here:
$(METADATA): Makefile
	@touch $(METADATA)
	@echo "Owner:        Bastien Nocera <bnocera@redhat.com>" > $(METADATA)
	@echo "Name:         $(TEST)" >> $(METADATA)
	@echo "Path:         $(TEST_DIR)"	>> $(METADATA)
	@echo "TestVersion:  $(TESTVERSION)"	>> $(METADATA)
	@echo "License:		 RH Internal Test" >> $(METADATA)
	@echo "Description:  Tests if sed handles escapes correctly">> $(METADATA)
	@echo "TestTime:     1m" >> $(METADATA)
	@echo "RunFor:       $(PACKAGE_NAME) " >> $(METADATA)  # add any other packages for which your test ought to run here
	@echo "Requires:     $(PACKAGE_NAME) " >> $(METADATA)  # add any other requirements for the script to run here
	@echo "Priority:     Normal" >> $(METADATA)
	@echo "Type:         Regression " >> $(METADATA)
	rhts-lint $(METADATA)

