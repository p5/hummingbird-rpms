#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/openldap/Sanity/smoke-test
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
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="openldap"

PACKAGES=("openldap"           \
          "openldap-clients"   \
          "openldap-servers"   \
          "cyrus-sasl-devel"   \
          "gdbm-devel"         \
          "libtool"            \
          "krb5-devel"         \
          "openssl-devel"      \
          "pam-devel"          \
          "perl"               \
          "unixODBC-devel"     \
          "libtool-ltdl-devel" \
          "nfs-utils"          \
          "rpm-build"          \
          "nss-devel"          \
          "libdb-devel"        \
          "groff"              \
          "cracklib-devel"     \
          "perl-ExtUtils-Embed"\
          "pkgconf-pkg-config" )

LDAP_SERVICE='slapd'

rlJournalStart

    rlPhaseStartSetup "General Setup"

        rlRun "TmpDir=$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"

        for P in "${PACKAGES[@]}"; do rlCheckRpm $P || rlDie; done

        rlFetchSrcForInstalled $PACKAGE
        rlRun "yum-builddep -y openldap*src.rpm" 0
        rlRun "rpm -ihv *.rpm" 0

        rlServiceStop $LDAP_SERVICE

    rlPhaseEnd

    rlPhaseStartTest

        TOPDIR=$(rpm --eval %_topdir)
        rlRun "pushd $TOPDIR" 0

        rlRun "rpmbuild -vv -bc SPECS/openldap.spec >build.log 2>&1" 0
        [[ $? -ne 0 ]] && cat build.log
        VERSION=$(rpm -q --qf "%{VERSION}\n" openldap | tail -1)
        rlRun "pushd BUILD/openldap-${VERSION}-build/openldap-${VERSION}/openldap-${VERSION}" 0
        # workaround for failing test, it tests unsupported configuration
        # see http://www.openldap.org/lists/openldap-technical/201204/msg00080.html for upstream reply
        # change of check after test is not enough because run of all tests with hdb is skipped if test058 fails with bdb
        #rm -f tests/scripts/test058-syncrepl-asymmetric

        rlRun "make check > make_check.out 2>&1" 0

        grep ">>>>" make_check.out > make_check.results
        cat make_check.out
        echo -e "\n\nResults:\n\n"
        cat make_check.results

        rlAssertNotGrep "failed" make_check.results

        rlRun "popd" 0
        rlRun "popd" 0
    rlPhaseEnd

    rlPhaseStartCleanup

        rlServiceRestore $LDAP_SERVICE
        rlRun "rm -rf BUILD/opendap-$(rpm -q --qf "%{VERSION}" openldap)" 0
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"

    rlPhaseEnd

rlJournalPrintText

rlJournalEnd
