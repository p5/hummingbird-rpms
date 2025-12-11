#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/GNU-Attribute-notes-not-recognized
#   Description: GNU-Attribute-notes-not-recognized
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2018 Red Hat, Inc.
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

PACKAGE="elfutils"

rlJournalStart
    rlPhaseStartTest
        # Rely on that /bin/bash is annobin-annotated per
        # - https://fedoraproject.org/wiki/Toolchain/Watermark
        # - https://fedoraproject.org/wiki/Changes/Annobin
        # Seems to work fine with bash-4.4.19-6.el8 and elfutils-0.174-5.el8.
        f="/bin/bash"

        # Annobin notes originally used to reside in the binary itself.
        # Later on they moved to debuginfo.
        # Let's see if we can chase down needed debuginfo somewhere...

        # Attempt getting the needed file using debuginfod
        export DEBUGINFOD_URLS=https://debuginfod.fedoraproject.org/
        rlRun "f=\"$f $(debuginfod-find debuginfo /bin/bash)\""

        # Attempt getting the needed file by traditional means
        rlRun "debuginfo-install -y bash"
        rlRun "buildid=$(eu-readelf -n /bin/bash | awk '/Build ID:/ {print $NF}')"
        for i in $(rpm -ql bash-debuginfo); do
            test -f $i || continue
            if eu-readelf -n $i | fgrep $buildid; then
                rlRun "f=\"$f $i\""
            fi
        done

        set -o pipefail
        export f
        # Check if eu-readelf can read the notes from at least one of files
        # that can possibly contain it...
        rlRun "(for i in $f; do eu-readelf -n $i; done ) | grep -2 '^  GA' | fgrep 'GNU Build Attribute' | tail -50"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
