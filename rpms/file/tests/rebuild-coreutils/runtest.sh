#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of file/tests/rebuild-coreutils
#   Description: Rebuild coreutils
#   Author: Milos Prchlik <mprchlik@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2015 Red Hat, Inc.
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

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGES="file rpm-build"
TEST_PACKAGE="${TEST_PACKAGE:-coreutils}"
TEST_USER="${TEST_USER:-jouda}"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm --all

        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd \$TmpDir"


        rlRun "dnf install -y $TEST_PACKAGE"
        rlRun "rlFetchSrcForInstalled $TEST_PACKAGE"
        rlRun "SRPM=\$(find . -name '$TEST_PACKAGE-*.src.rpm')"
        rlRun "dnf builddep -y $SRPM"

        rlRun "userdel -r $TEST_USER" 0,6
        rlRun "useradd -m -d /home/$TEST_USER $TEST_USER"
        rlRun "cp $SRPM /home/$TEST_USER"
        rlRun "su - $TEST_USER -c 'rpm -Uvh $SRPM'"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "su - $TEST_USER -c 'rpmbuild -ba --clean --nocheck \$(rpm --eval=%_specdir)/$TEST_PACKAGE.spec'"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "userdel -r $TEST_USER"
        rlRun "popd"
        rlRun "rm -r \$TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
