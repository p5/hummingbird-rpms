#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tests/Regression/rawhide-enable
#   Description: Tries enabling rawhide and upgrading after it
#   Author: Petr Mensik <pemensik@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2020 Red Hat, Inc.
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

PACKAGE="fedora-repos"

basearch() {
	dnf config-manager --dump-variables | sed -e '/^basearch\s*=/ ! d' -e 's/^[^=]*=\s*//'
}

test_keyring() {
	rlRun "KEYRING=$(mktemp --tmpdir keyring.XXXXXXX)"
	rlRun "BASEARCH=$(basearch)"
	rlRun "gpg --no-default-keyring --keyring $KEYRING --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$RAWHIDE_RELEASE-$BASEARCH" 0 "Test import of rawhide key"
	rlRun "rm -f $KEYRING"
}

rlJournalStart
  if rpm -q $PACKAGE-rawhide; then
    rlPhaseStartTest
	rlLogWarning "This test should test stable releases, not rawhide!"
	# Just check GPG key can be imported on this arch
	rlRun "RAWHIDE_RELEASE=$(rpm -q fedora-repos-rawhide | cut -d- -f4)"
	test_keyring
    rlPhaseEnd
  else
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
	rlAssertNotRpm $PACKAGE-rawhide # rawhide should not yet be installed at this point
	rlRun "dnf -y upgrade fedora-repos fedora-gpg-keys"
	rlRun "dnf -y install fedora-repos-rawhide"
	rlRun "dnf config-manager --set-enabled rawhide"
	rlRun "RAWHIDE_RELEASE=$(dnf --repo rawhide repoquery fedora-repos | sed -e 's/fedora-repos-\(0:\)\?\([0-9]\+\)-.*/\2/')" 0 "Find rawhide version"
    rlPhaseEnd

    rlPhaseStartTest
	# Until proposal https://pagure.io/releng/issue/7445 is solved, this might fail
	rlRun "dnf -y upgrade fedora-gpg-keys" 0,1 "Try normal upgrade"
	# Ensure it works with manual release increment
	rlRun "dnf -y --repo rawhide --releasever $RAWHIDE_RELEASE upgrade fedora-gpg-keys" 0 "Upgrade with bumped release"
	test_keyring
    rlPhaseEnd

    rlPhaseStartCleanup
	rlRun "dnf config-manager --set-disabled rawhide"
	rlRun "dnf -y downgrade fedora-gpg-keys fedora-repos-rawhide" 0 "Cleanup dnf changes back"
	rlRun "dnf -y remove --noautoremove fedora-repos-rawhide"
    rlPhaseEnd
  fi
rlJournalPrintText
rlJournalEnd
