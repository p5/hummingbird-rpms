# runtest.sh - uppercase-operand
# Author: Petr Muller <pmuller@redhat.com>
# Location: /CoreOS/sed/Regression/uppercase-operand/runtest.sh

# Description: Verifiies that sed correctly processes an 'u' operand, which returns uppercase of matched character

# Copyright (c) 2008 Red Hat, Inc. All rights reserved. This copyrighted material 
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


PACKAGE=sed

RESULT=FAIL
SCORE=0

if rpm -q $PACKAGE &>/dev/null; then
	PKG_VERS=$( rpm -q ${PACKAGE} --queryformat %{version} )
	PKG_RELEASE=$( rpm -q ${PACKAGE} --queryformat %{release} )
fi

# Include rhts environment
. /usr/bin/rhts-environment.sh

function Log {
	echo -e ":: [`date +%H:%M:%S`] :: $1" >> $OUTPUTFILE
}

function HeaderLog {
	echo -e "\n::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::" >> $OUTPUTFILE
	echo -e ":: [`date +%H:%M:%S`] :: $1" >> $OUTPUTFILE
	echo -e "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n" >>$OUTPUTFILE
}

HeaderLog "Starting $PACKAGE RHTS Test"

if rpm -q $PACKAGE &>/dev/null; then 
	Log "Running $PACKAGE-$PKG_VERS-$PKG_RELEASE"
else
	Log "WARNING: Unable to locate $PACKAGE"  	
fi

	####################
	# Begin Test-Case
	# Find result should be PASS or FAIL
	####################

HeaderLog "Starting Test-Case"

testcase='i shouLD be In UpPeR CaSe, yeah, I should'
Log "Testcase: '$testcase'"
res=`echo $testcase | sed -e 's/[a-z]/\u&/g'`
Log "Result: $res"

	####################
	# Check Results
	####################
	
HeaderLog "Checking Results"
if [ "$res" == "I SHOULD BE IN UPPER CASE, YEAH, I SHOULD" ]
then
  RESULT=PASS
  Log "Seems correct: PASS"
else
  RESULT=FAIL
  Log "Didn't get what we expected: FAIL"
fi

HeaderLog "Reporting Results"

Log "TEST: $TEST | RESULT: $RESULT\n"
report_result $TEST $RESULT

HeaderLog "End of $PACKAGE RHTS Test"
