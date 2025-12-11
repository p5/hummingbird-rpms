#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/sed/Sanity/selftest
#   Description: Execute test suite comming with sed
#   Author: Miroslav Vadkerti <mvadkert@redhat.com>
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

PACKAGE="sed"
PACKAGES="sed gcc rpm-build automake libselinux-devel glibc-devel"
UPSTREAMPKG="sed-*"
BUILDLOG=`mktemp`
TESTLOG=`mktemp`
TARGET=$(echo `uname -m` | egrep ppc)
if [[ $TARGET != "" ]]; then 
	if rlIsRHEL 4; then
		TARGET="--target ppc"
	else
		TARGET="--target `uname -m`"
	fi
fi

rlJournalStart
    rlPhaseStartSetup
    	for PKG in $PACKAGES; do
	        rlAssertRpm $PKG
	done
	rlFetchSrcForInstalled $PACKAGE
	# make sure all deps installed
	if ! rlIsRHEL 3 4 5; then
		rlRun "yum-builddep -y *.src.rpm" 0-255
	fi
    rlPhaseEnd

    rlPhaseStartTest
	rlRun "rpm -ivh $PACKAGE*.src.rpm" 0 "Installing $PACKAGE src rpm"
SRCDIR="/usr/src/redhat"
if ! rlIsRHEL 3 4 5; then
	SRCDIR="$HOME/rpmbuild/"
	echo "+ RHEL6+ detected: SRCDIR=$SRCDIR"
fi
SPEC="$SRCDIR/SPECS/$PACKAGE*.spec"
TESTDIR="$SRCDIR/BUILD/$UPSTREAMPKG/"
	echo "+ Building $PACKAGE (Log: $BUILDLOG)"
	echo "+ Build command: rpmbuild -bc $SPEC $TARGET"
	rlRun "rpmbuild -bc $SPEC $TARGET &> $BUILDLOG"
	echo "+ Buildlog:"
	tail -n 100 $BUILDLOG
	rlRun "pushd ."
 	rlRun "cd $TESTDIR"
	# disable test known to fail when run as root
	rlRun "sed -i 's/testsuite\/panic-tests.sh//' Makefile.in"
	rlRun "make check &> $TESTLOG"   
	cat $TESTLOG
	rlAssertNotGrep "^FAIL" $TESTLOG
    rlPhaseEnd

    rlPhaseStartCleanup
    	rlRun "popd"
	rlRun "rm -rf $PACKAGE*.src.rpm" 0 "Removing source rpm"    
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
