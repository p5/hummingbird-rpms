#!/bin/bash
# vim: dict=/usr/share/rhts-library/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/findutils/Sanity/options/xautofs
#   Description: Check xautofs option
#   Author: Petr Splichal <psplicha@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2009 Red Hat, Inc. All rights reserved.
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

PACKAGE="findutils"

MasterConf="/etc/auto.master"
DirectConf="/etc/auto.direct"

MountDir="/mnt/findutils"
AutomountDir="$MountDir/etc"
RegularDir="$MountDir/regular/directory/master"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlAssertRpm "autofs"
        rlRun "set -o pipefail"

        # create dirs & back up
        rlRun "TmpDir=\`mktemp -d\`" 0 "Creating tmp directory"
        rlRun "mkdir -p $RegularDir" 0 "Creating regular directory"
        rlRun "rlFileBackup $MasterConf"

        # set up autofs
        rlRun "echo '/- /etc/auto.direct' > $MasterConf" \
                0 "Setting up autofs master map"
        rlRun "echo '$AutomountDir localhost:/etc' > $DirectConf" \
                0 "Setting up autofs direct map"

        # get fstype of /etc
        fs="$(df --output=fstype /etc/ | tail -n1)"

        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest "Without -xautofs option"
        rlRun "rlServiceStart autofs" 0 "Starting autofs"
        rlAssertNotGrep "$AutomountDir.*$fs" "/proc/mounts"
        rlRun "find $MountDir -noleaf -name '*master*' | tee filelist"
        rlAssertGrep "$RegularDir" "filelist"
        rlAssertGrep "$MountDir$MasterConf" "filelist"
        rlAssertGrep "$AutomountDir.*$fs" "/proc/mounts"
    rlPhaseEnd

    rlPhaseStartTest "With -xautofs option"
        rlRun "rlServiceStart autofs" 0 "Starting autofs"
        rlAssertNotGrep "$AutomountDir.*$fs" "/proc/mounts"
        rlRun "find $MountDir -xautofs -noleaf -name '*master*' | tee filelist"
        rlAssertGrep "$RegularDir" "filelist"
        rlAssertNotGrep "$MountDir$MasterConf" "filelist"
        rlAssertNotGrep "$AutomountDir.*$fs" "/proc/mounts"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rlFileRestore"
        rlRun "rlServiceRestore autofs"
        rlRun "umount --all --types autofs"
        rlRun "rm -r $TmpDir $DirectConf $MountDir" 0 "Removing tmp files"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
