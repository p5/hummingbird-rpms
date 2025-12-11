#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/file/Sanity/command-line-options
#   Description: Test (most of) command line options available for the file command.
#   Author: Karel Srot <ksrot@redhat.com>
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
. /usr/share/beakerlib/beakerlib.sh

PACKAGE="file"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\`mktemp -d\`" 0 "Creating tmp directory"
	rlRun "cp file_cmd_line_options.tar.gz $TmpDir" 0 "Copying sample files"
        rlRun "pushd $TmpDir"
	rlRun "tar -xzf file_cmd_line_options.tar.gz" 0 "Extracting sample files"
    rlPhaseEnd

    rlPhaseStartTest "--brief"
        rlRun "file -b dummy_file | grep -q dummy_file" 1 "Checking -b"
        rlRun "file --brief dummy_file | grep -q dummy_file" 1 "Checking --brief"
    rlPhaseEnd

    rlPhaseStartTest "--exclude"
        rlRun "file /bin/bash | grep -q 'dynamically linked'"
	rlRun "file -e elf /bin/bash | grep -q 'dynamically linked'" 1 "Checking -e elf"
	rlRun "file --exclude elf /bin/bash | grep -q 'dynamically linked'" 1 "Checking --exclude elf"
    rlPhaseEnd

    rlPhaseStartTest "--files-from"
        rlRun 'file -f list.txt | grep -q /dev/zero' 0 "Checking -f file"
        rlRun 'echo "/dev/zero" | file -f - | grep -q /dev/zero' 0 "Checking -f -"
        rlRun 'file --files-from list.txt | grep -q /dev/zero' 0 "Checking --files-from file"
        rlRun 'echo "/dev/zero" | file --files-from - | grep -q /dev/zero' 0 "Checking --files-from -"
    rlPhaseEnd

    rlPhaseStartTest "--separator"
	rlRun "file -F '#' dummy_file | grep -q 'dummy_file#'" 0 "Checking -F"
	rlRun "file --separator '#' dummy_file | grep -q 'dummy_file#'" 0 "Checking --separator"
    rlPhaseEnd

  if ! rlIsRHEL 4; then   # not for RHEL4
    rlPhaseStartTest "--no-dereference"
	rlRun "POSIXLY_CORRECT=1 file symlink | grep -q 'symlink: ASCII text'" 0 "Checking -h" 
	rlRun "POSIXLY_CORRECT=1 file -h symlink | grep -q 'symlink: symbolic link'" 0 "Checking -h"
	rlRun "POSIXLY_CORRECT=1 file symlink | grep -q 'symlink: ASCII text'" 0 "Checking --no-dereference" 
	rlRun "POSIXLY_CORRECT=1 file --no-dereference symlink | grep -q 'symlink: symbolic link'" 0 "Checking --no-dereference"
    rlPhaseEnd
  fi

    rlPhaseStartTest "--mime"
	rlRun "file -i dummy_file | grep -q 'text/plain; charset=us-ascii'" 0 "Checking -i"
	rlRun "file --mime dummy_file | grep -q 'text/plain; charset=us-ascii'" 0 "Checking --mime"
    rlPhaseEnd

    rlPhaseStartTest "--dereference"
	rlRun "file -L symlink | grep -q 'symbolic link'" 1 "Checking -L" 
	rlRun "file -L symlink | grep -q 'ASCII text'" 0 "Checking -L"
	rlRun "file --dereference symlink | grep -q 'symbolic link'" 1 "Checking --dereference" 
	rlRun "file --dereference symlink | grep -q 'ASCII text'" 0 "Checking --dereference"
    rlPhaseEnd

    rlPhaseStartTest "--keep-going"
	rlRun "file -k two_types.txt | grep 'Future Composer' | grep 'Apple QuickTime'" 0 "Checking -k" 
	rlRun "file --keep-going two_types.txt | grep 'Future Composer' | grep 'Apple QuickTime'" 0 "Checking --keep-going" 
    rlPhaseEnd

    rlPhaseStartTest "--no-pad"
	rlRun 'WC1=`file dummy_file symlink | grep symlink | wc -c`; echo $WC1'
	rlRun 'WC2=`file symlink | wc -c`;echo $WC2'
	rlRun 'WC3=`file -N dummy_file symlink | grep symlink | wc -c`;echo $WC3'
	rlRun '[ $WC1 -gt $WC3 -a $WC2 -eq $WC3 ]' 0 "Checking -N"
	rlRun 'WC3=`file --no-pad dummy_file symlink | grep symlink | wc -c`;echo $WC3'
	rlRun '[ $WC1 -gt $WC3 -a $WC2 -eq $WC3 ]' 0 "Checking --no-pad"
    rlPhaseEnd

    rlPhaseStartTest "--preserve-date"
	rlRun 'touch dummy_file; TS1=`stat -c "%X" dummy_file`;echo $TS1; sleep 3'
	rlRun 'file -p dummy_file; TS2=`stat -c "%X" dummy_file`;echo $TS2'
	rlRun 'file dummy_file; TS3=`stat -c "%X" dummy_file`;echo $TS3'
	rlRun '[ $TS3 -gt $TS1 -a $TS1 -eq $TS2 ]' 0 "Checking -p"
	rlRun 'touch dummy_file; TS1=`stat -c "%X" dummy_file`;echo $TS1; sleep 3'
	rlRun 'file --preserve-date dummy_file; TS2=`stat -c "%X" dummy_file`;echo $TS2'
	rlRun 'file dummy_file; TS3=`stat -c "%X" dummy_file`;echo $TS3'
	rlRun '[ $TS3 -gt $TS1 -a $TS1 -eq $TS2 ]' 0 "Checking --preserve-date"
    rlPhaseEnd

    rlPhaseStartTest "--special-files"
	rlRun "file /dev/zero | grep -q 'character special'" 
	rlRun "file -s /dev/zero | grep -q 'data'" 0 "Checking -s"
	rlRun "file --special-files /dev/zero | grep -q 'data'" 0 "Checking --special-files"
    rlPhaseEnd

    rlPhaseStartTest "--version"
	rlRun "file -v 2>&1 | grep -E 'file-[[:digit:]]\.[[:digit:]]'" 0  "Checking -v"
	rlRun "file --version 2>&1 | grep -E 'file-[[:digit:]]\.[[:digit:]]'" 0  "Checking --version"
    rlPhaseEnd

  if ! rlIsRHEL 4; then   # not for RHEL4 - this will never be fixed
    rlPhaseStartTest "--uncompress"
	rlRun "file dummy_file.bz2 | grep -q 'ASCII text'" 1
	rlRun "file -z dummy_file.bz2 | grep -q 'ASCII text'" 0 "Checking -z"
	rlRun "file --uncompress dummy_file.bz2 | grep -q 'ASCII text'" 0 "Checking --uncompress"
    rlPhaseEnd

    rlPhaseStartTest "--help"
	rlRun "file --help 2>&1 | grep -iq 'usage:'" 0 "Checking --help"
    rlPhaseEnd
  fi

    if [ `rlGetDistroRelease` -ge 6 ]; then

	rlPhaseStartTest "--mime-type"
	    rlRun "file --mime-type dummy_file | grep -q 'text/plain'" 0 "Checking --mime-type"
	    rlRun "file --mime-type dummy_file | grep -q 'us-ascii'" 1 "Checking --mime-type"
	rlPhaseEnd

	rlPhaseStartTest "--mime-encoding"
	    rlRun "file --mime-encoding dummy_file | grep -q 'text/plain'" 1 "Checking --mime-encoding"
	    rlRun "file --mime-encoding dummy_file | grep -q 'us-ascii'" 0 "Checking --mime-encoding"
	rlPhaseEnd

        rlPhaseStartTest "--print0"
	    rlRun "file -0 dummy_file | cat -A | grep -q 'dummy_file^@:'" 0 "Checking -0"
	    rlRun "file --print0 dummy_file | cat -A | grep -q 'dummy_file^@:'" 0 "Checking --print0"
        rlPhaseEnd
    fi

    rlPhaseStartCleanup
	rlRun "popd"
	rlRun "rm -rf $TmpDir" 0 "Deleting tmp directory"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
