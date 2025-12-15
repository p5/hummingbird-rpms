#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/p11-kit/trust-anchor-complains-about-invalid-attribute-and
#   Description: Test for trust anchor complains about invalid attribute and
#   Author: Hubert Kario <hkario@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2017 Red Hat, Inc.
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

PACKAGE="p11-kit"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "rlFileBackup --clean /etc/pki"
    rlPhaseEnd

    rlPhaseStartTest
        DUMMY_MAKER_BIN="/etc/pki/tls/certs/make-dummy-cert"
        [ -x /usr/bin/make-dummy-cert ] && DUMMY_MAKER_BIN="/usr/bin/make-dummy-cert"
        rlRun "$DUMMY_MAKER_BIN mycert-tmp.pem"
        rlRun "openssl x509 -in mycert-tmp.pem -addtrust clientAuth -addtrust serverAuth -addtrust emailProtection -out mycert.pem"
        rlAssertNotExists "/etc/pki/ca-trust/source/localhost.localdomain.p11-kit"
        rlRun -s "trust anchor --store mycert.pem"
        rlAssertNotGrep "p11-kit:" $rlRun_LOG
        rlAssertExists "/etc/pki/ca-trust/source/localhost.localdomain.p11-kit"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rlFileRestore"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
