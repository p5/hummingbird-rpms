#!/bin/bash

# Tests if sed handles escapes correctly

ACTUALFILE=`mktemp`
EXPECTEDFILE=`mktemp`
RETVAL=1

echo '' | sed -e ' i\\co' > $ACTUALFILE
printf '\x0f\n\n' > $EXPECTEDFILE

if diff $EXPECTEDFILE $ACTUALFILE > /dev/null; then
	RETVAL=0
	echo "Succeeded"
else
	echo "Failed"
fi

rm -f $ACTUALFILE $EXPECTEDFILE

exit $RETVAL
