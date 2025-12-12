#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/libtasn1/Sanity/smoke-test
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

# Include rhts environment
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="libtasn1"

PACKAGES=( "libtasn1" "valgrind" )

TOPDIR=`rpm --eval %_topdir`

rlJournalStart

    rlPhaseStartSetup     
        for P in "${PACKAGES[@]}"; do rlAssertRpm $P || rlDie; done
	rlFetchSrcForInstalled $PACKAGE
        rlRun "dnf builddep -y libtasn1*.rpm"
 	rlRun "rpm -ihv `ls libtasn1*.rpm`" 0
	rlRun "rpmbuild -vv -bc $TOPDIR/SPECS/libtasn1.spec" 0
    rlPhaseEnd

    rlPhaseStartTest

	rlRun "make -C $TOPDIR/BUILD/libtasn1-* check > make_check.out" 0
	cat make_check.out	

	if grep "All [0-9]\+ tests passed" make_check.out; then
            rlPass "All tests passed -- have seen the old format of test summary in the output"
        elif grep "Testsuite summary" make_check.out; then
            TOTAL=`sed -rn 's/^# TOTAL: *([0-9]*).*/\1/p' make_check.out`
            PASS=`sed -rn 's/^# PASS: *([0-9]*).*/\1/p' make_check.out`
            rlAssertEquals "The number of tests that ran and passed should be equal" "$TOTAL" "$PASS"
        else
            rlFail "Tests reported summary in an unknown way"
            rlBundleLogs make_check.out
        fi

    rlPhaseEnd

    rlPhaseStartCleanup
	rlRun "rm libtasn1*.rpm -rf" 0
	rlRun "rm $TOPDIR/BUILD/libtasn1-* -rf" 0
    rlPhaseEnd

rlJournalPrintText

rlJournalEnd
