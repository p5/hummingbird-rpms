#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/gawk/Regression/printf-format-s-in-gawk-not-working
#   Description: Test for printf format "%.*s" in gawk not working
#   Author: David Kutalek <dkutalek@redhat.com>
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

# Include rhts environment
. /usr/bin/rhts-environment.sh
. /usr/lib/beakerlib/beakerlib.sh

PACKAGE="gawk"
REPRODUCER="echo ab123dl|gawk '{printf(\"%.*s\\n\",length(\$0)-1,\$0)}'"
EXPECTED_RESULT="ab123d"

rlJournalStart

    rlPhaseStartTest
        rlAssertRpm $PACKAGE
	rlLog "Bug reproducer: $REPRODUCER"
	rlRun "$REPRODUCER | tee /tmp/$NAME-result.txt"  0 "Running reproducer"
	RESULT="`cat /tmp/$NAME-result.txt`"
	rlAssertEquals "Result should be $EXPECTED_RESULT" "_$RESULT" "_$EXPECTED_RESULT"
	rm /tmp/$NAME-result.txt
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
