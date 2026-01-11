#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/cracklib/Sanity/ABI-compatibility
#   Description: Test if the ABI hasn't changed
#   Author: Hubert Kario <hkario@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2013 Red Hat, Inc. All rights reserved.
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

PACKAGE="cracklib"

if rlIsRHEL 5; then
PACKAGES="cracklib gcc words ltrace"
else
PACKAGES="cracklib cracklib-devel gcc words ltrace"
fi

rlJournalStart
    rlPhaseStartSetup
	for PKG in $PACKAGES; do
          rlAssertRpm $PKG
        done
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
	rlRun "if [ ! -e /usr/share/cracklib/pw_dict.pwi ]; then create-cracklib-dict /usr/share/dict/words; fi" 0 "Create a cracklib dictionary if not already present"
        rlRun "pushd $TmpDir"
	rlRun "cat > test.c <<_EOF_
#include <stdio.h>
#include <crack.h>

int main(int argc, char **argv)
{
  char const *dict = \"/usr/share/cracklib/pw_dict\";
  char const *msg = NULL;
  msg = FascistCheck(\"AAAAAAAA\", dict);
  if (msg == 0)
    return 1;
  else
  {
    printf(\"%s\\n\", msg);
    return 0;
  }
}
_EOF_" 0 "Create test application"
    rlPhaseEnd

    rlPhaseStartTest
	rlRun "gcc -O0 test.c -lcrack -Wall -o test" 0 "Compile the program"
	rlRun "./test" 0 "Run the program"
	rlRun "ltrace -o ltrace.out ./test" 0 "Run the program with ltrace"
	rlRun "grep FascistCheck ltrace.out" 0 "Check if it actually uses the library function"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
