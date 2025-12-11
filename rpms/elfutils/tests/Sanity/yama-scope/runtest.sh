#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/elfutils/Sanity/yama-scope
#   Description: yama-scope
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

PACKAGE="elfutils"
MY_USER="ptrace_scope_testuser"
TESTCASE="/tmp/ptrace-scope-test.sh"
PROCFILE='/proc/sys/kernel/yama/ptrace_scope'

test_root()
{
    $TESTCASE
}

test_user()
{
    su - $MY_USER -c $TESTCASE
}

rlJournalStart
    rlPhaseStartTest

# This can easily be tested with strace. Just cycle through the settings:

# 0 - Default attach security permissions.
# 1 - Restricted attach. Only child processes plus normal permissions.
# 2 - Admin-only attach. Only executables with CAP_SYS_PTRACE.
# 3 - No attach. No process may call ptrace at all. Irrevocable.

# echo 0 > /proc/sys/kernel/yama/ptrace_scope

# With 0, strace works against any process with your uid. For example, strace -p 2190.
# With 1, strace errors when doing the same as in 0: strace: attach: ptrace(PTRACE_SEIZE, 3180): Operation not permitted. However, you can strace any program you run from strace, "strace /bin/ls" or example.
# With 2, you can only strace from the root account. You can no longer strace commands run from strace.
# With 3, even root cannot strace.

# ---

# possible related AVCs tracked as https://bugzilla.redhat.com/show_bug.cgi?id=1458999

# ---

            rlRun "useradd $MY_USER" 0,9

            rlRun "cp ptrace-scope-test.sh /tmp/"
            rlRun "chmod a+rx /tmp/ptrace-scope-test.sh"

            rlRun "ORIGVAL=$( cat $PROCFILE )"

            # First, test the default behaviour, which is "no restriction"
            # from the ptrace perspective. Here we assume that
            # elfutils-default-yama-scope.rpm is installed and so the default
            # yama policy is set to 0 instead of 1 which would otherwise be set
            # as a kernel default (security/yama/yama_lsm.c ---> YAMA_SCOPE_RELATIONAL)
            rlRun test_root
            rlRun test_user

            rlRun "echo 0 > $PROCFILE"
            rlRun test_root
            rlRun test_user
            rlRun "echo 1 > $PROCFILE"
            rlRun test_root
            rlRun test_user 1
            rlRun "echo 2 > $PROCFILE"
            rlRun test_root
            rlRun test_user 1
            # Following subtest would be irrevertible (till next reboot)
            # rlRun "echo 3 > $PROCFILE"
            # rlRun test_root 1
            # rlRun test_user 1

            rlRun "userdel -f $MY_USER"

# This testcase could be more complex - using child and non-child processes and
# performing reboots.  But let's keep this simple, since we are not testing the
# kernel facility, but merely an elfutils "plugin" for it, whose purpose is to
# set the default yama policy as such.

            rlRun "echo $ORIGVAL > $PROCFILE"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
