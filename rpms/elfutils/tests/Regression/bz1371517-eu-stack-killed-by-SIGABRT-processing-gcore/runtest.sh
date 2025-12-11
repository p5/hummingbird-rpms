#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Regression/bz1371517-eu-stack-killed-by-SIGABRT-processing-gcore
#   Description: Test for BZ#1371517 (eu-stack killed by SIGABRT processing gcore)
#   Author: Martin Cermak <mcermak@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2017 Red Hat, Inc.
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

rlJournalStart
    rlPhaseStartSetup
        rlRun "rpm -q elfutils"
        rlRun "rpm -q gdb"
        rlRun "TMPD=\$(mktemp -d)"
        rlRun "pushd $TMPD"
    rlPhaseEnd

    rlPhaseStart FAIL "Build an unstripped binary"
	# ... so that we don't need to rely on the infra providing us with
	# a (coreutils-) debuginfo package.
	echo -e "#include <unistd.h>\nint main () { sleep(100); return 0; }" | gcc -g -xc -o sleep100 -
	rlRun "file sleep100 | fgrep 'not stripped'"
    rlPhaseEnd

    rlPhaseStartTest
        ./sleep100 &
        SLEEP_PID=$!
        rlRun "gcore $SLEEP_PID"
        # On some arches, such as aarch64, or s390x, eu-stack doesn't end at some
        # reasonable point, when printing the trace, and goes across main, to
        # __libc_start_main and even higher and then finally complains about
        # "no matching address range".  But we don't want to be so strict to check
        # for this right now.  Mark Wielaard says it is okay, so I trust him ...
        # Following assert fails when we get SEGV, which would be bz1371517, which
        # reproduces e.g. on f25 using elfutils-0.166-2.fc25, or on rhel-7.3
        # using elfutils-0.166-2.el7.
        rlRun "eu-stack --executable=./sleep100 --core=core.$SLEEP_PID > output.txt" 0,1
        # Print the output.  Yeah, this could be done using tee or something in
        # the above line and play games with exitcodes within a pipe chain, but
        # this actually is https://en.wikipedia.org/wiki/KISS_principle :)
        rlRun "cat output.txt"
        # ... we do want to check at least that "main" was listed in the trace.
        rlRun "awk {'print \$3'} output.txt | grep ^main$"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TMPD"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
