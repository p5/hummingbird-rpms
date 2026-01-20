#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/chrpath/Regression/internal-tests
#   Description: internal-tests
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2016 Red Hat, Inc.
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation, either version 2 of
#   the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see http://www.gnu.org/licenses/.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

CMD='chrpath'
BIN=$(which --skip-alias $CMD)
PACKAGE="${PACKAGE:-$(rpm -qf --qf='%{name}\n' $BIN)}"
export PACKAGE

ORIGWD=$(pwd)

# To test the compat arch stuff, we need the compat arch compiler capability.
# Ideally the test harness should install it, since respective 32/31 bit runtime
# requirements (libgcc, glibc-devel) are mentioned as requirements in the Makefile
# but just in case that would fail, we'll try to fix this now at the test run time.
if arch | egrep -q '(x86_64|ppc64|s390x)'; then
    b='-m32'
    arch | grep s390x && b='-m31'
    echo "int main() { return 0; }" | gcc -m32 -xc -o /dev/null - || \
	yum -y install --setopt=multilib_policy=all libgcc glibc-devel
fi

rlJournalStart
    rlPhaseStartSetup
        rlRun "TMPD=$(mktemp -d)"
        rlRun "pushd $TMPD"
	rlFetchSrcForInstalled $PACKAGE
	rlRun "rpm --define='_topdir $TMPD' -Uvh *src.rpm"
	rlRun "rpmbuild --define='_topdir $TMPD' -bc SPECS/${CMD}.spec"
    rlPhaseEnd

    rlPhaseStartTest
	rlRun "pushd BUILD/$CMD-*"
	# Some CI systems complain about "C compiler cannot create executables"
	# Not really sure what's going on there, thus printing the config.log:
	rlRun "cat config.log"
	# To run the testsuite for compat arch, we need to patch the testsuite
	# per https://bugzilla.redhat.com/show_bug.cgi?id=1271380#c25. But just
	# in case the patch wouldn't apply, we'll first run the unpatched tests
	# so that we have at least some results and then try to patch and rerun.
	rlRun "make check"
	RUN_SEC_ARCH="false"
	RHEL_VERSION=$(rpm --eval %{rhel})
	[[ $RHEL_VERSION -ge 7 ]] && arch | egrep -q '(x86_64|ppc64)' && RUN_SEC_ARCH="true"
	[[ $RHEL_VERSION -eq 7 ]] && arch | egrep -q '(s390x)' && RUN_SEC_ARCH="true"

	if [ "$RUN_SEC_ARCH" = "true" ]; then
	    rlRun "patch -p1 < $ORIGWD/testsuite.patch"
	    rlRun "make check"
	fi
	rlRun "popd"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TMPD"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
