#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/python-requests/Sanity/upstream
#   Description: Runs upstream test suite
#   Author: Lukas Zachar <lzachar@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2019 Red Hat, Inc.
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

PACKAGES="${PACKAGES:-python3-requests}"
PYTHON="${PYTHON:-python}"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm --all
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"

        # So we can inject version of srpm
        if [[ -z "$FORCE_SRPM" ]]; then
            rlRun "rlFetchSrcForInstalled $(rpm --qf '%{name}' -qf $($PYTHON -c 'import requests;print(requests.__file__)'))"
        else
            rlRun "rlRpmDownload $FORCE_SRPM"
        fi
        rlRun "rpm -i --define '_topdir $TmpDir' --nodeps *rpm"
        rlRun "rpmbuild -bp --define '_topdir $TmpDir' --nodeps $TmpDir/SPECS/*"

        # Remove module from extracted sources so installed one is used
        rlRun "rm -rf $TmpDir/BUILD/*requests*/requests*/src"

        # pip-install libraries not in the repos
        # pytest is installed in fmf requirement
        rlRun "$PYTHON -m pip install pytest-mock==3.14.0 trustme==1.2.0 werkzeug==3.1.3 \
                pytest-httpbin==2.1.0"

        # Move to test dir, print what is there
        rlRun "cd $(dirname $TmpDir/BUILD/*requests*/requests*/tests)"
        rlRun "touch tests/requirements-dev.txt"
        rlRun "find . -type f"
        rlRun "yum repolist"
        rlRun "$PYTHON -m pip list"
    rlPhaseEnd

    rlPhaseStartTest "$EXTRA_PARAMS"
        # test_unicode_header_name hangs with urllib3 < 2
        rlRun 'pytest -v -p no:warnings --junit-xml $TmpDir/result.xml -k "not test_use_proxy_from_environment and not test_unicode_header_name"'

        rlAssertGrep '<testcase' $TmpDir/result.xml
    rlPhaseEnd

    rlPhaseStartCleanup
        # upload log if test failed
        rlGetTestState || rlRun "rlFileSubmit $TmpDir/result.xml"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
