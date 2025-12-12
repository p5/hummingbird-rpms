#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/libtasn1/Regression/libtasn1-doesn-t-handle-OIDs-which-have-elements
#   Description: Test for libtasn1 doesn't handle OIDs which have elements
#   Author: Hubert Kario <hkario@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2016 Red Hat, Inc.
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
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="libtasn1"

TOP_DIR="$(rpm --eval=%{_topdir})"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "echo 'PKIX1 { }

DEFINITIONS IMPLICIT TAGS ::=

BEGIN

Dss-Sig-Value ::= SEQUENCE {
    r       OBJECT IDENTIFIER,
    s       INTEGER
}
END' > pkix.asn"
        rlRun "echo 'dp PKIX1.Dss-Sig-Value
r 1.3.6.1.4.1.2312.9.2.1461701120873.1.6
s 255' > assign.asn1"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "asn1Coding pkix.asn assign.asn1"
        rlAssertGrep "1.3.6.1.4.1.2312.9.2.1461701120873.1.6" $rlRun_LOG
        rlRun "rm $rlRun_LOG"
        rlRun -s "openssl asn1parse -in assign.out -inform DER"
        rlAssertGrep "1.3.6.1.4.1.2312.9.2.1461701120873.1.6" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
