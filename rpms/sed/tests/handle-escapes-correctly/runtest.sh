#!/bin/sh

# Package: Package under test (will be used to get version info on executed
# tests). If RPM query results on PACKAGE are null, then pass value of
# PACKAGE variable for Version
PACKAGE=sed

# source the test script helpers
# BUG: This line is intentionally left commented out.
# When I have the helper packages installed the line below should be
# uncommented
. /usr/bin/rhts-environment.sh

# Commands in this section are provided by test developer.
# ---------------------------------------------


# Assume the test will pass.
result=PASS

# Run the acutal test and redirect the output to the log file
# So if need be we will have the debug info after the fact.
./handle-escapes-correctly.sh > $OUTPUTFILE
if [ $? -ne 0 ]; then
        result=FAIL
fi

echo $result

# Then file the results in the database
#------------------------------------------------
report_result $TEST $result

