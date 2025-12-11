#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/file/Sanity/Support-local-additions-to-magic-files
#   Description: Test to support local additions to magic files
#   Author: Karel Srot <ksrot@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
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
. /usr/share/beakerlib/beakerlib.sh

PACKAGE="file"

FILEBACKUP=''

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
	[ -f /etc/magic ] && FILEBACKUP=1 && rlFileBackup /etc/magic
	[ -f $HOME/.magic ] && FILEBACKUP=1 && rlFileBackup $HOME/.magic
	[ -f $HOME/.magic.mgc ] && FILEBACKUP=1 && rlFileBackup $HOME/.magic.mgc
	rm -f /etc/magic $HOME/.magic $HOME/.magic.mgc
	rlRun "echo '0 string MYFILEFORMAT1 My file format version1' > /etc/magic"
	rlRun "echo '0 string MYFILEFORMAT2 My file format version2' > $HOME/.magic"
	rlRun "echo 'MYFILEFORMAT1' > testfile1"
	rlRun "echo 'MYFILEFORMAT2' > testfile2"
	rlRun "echo 'MYFILEFORMAT3' > testfile3"
    rlPhaseEnd

    rlPhaseStartTest 
	rlRun "file testfile1 &> out1" 0 "Testing pattern from /etc/magic"
	cat out1
	rlRun "grep 'My file format version1' out1" 0 "File should be identified as 'My file format version1'"

	rlRun "file testfile2 &> out2" 0 "Testing pattern from $HOME/.magic"
	cat out2
	rlRun "grep 'My file format version2' out2" 0 "File should be identified as 'My file format version2'"
	
	pushd $HOME; 
	rlRun "file -C -m .magic" 0 "Preparing $HOME/.magic.mgc"
	ls -l $HOME/.magic.mgc
	rm -f $HOME/.magic
	popd
	
	rlRun "file testfile2 &> out3" 0 "Testing pattern from $HOME/.magic.mgc"
	cat out3
	rlRun "grep 'My file format version2' out3" 0 "File should be identified as 'My file format version2' too"

    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $TmpDir /etc/magic $HOME/.magic $HOME/.magic.mgc" 0 "Removing tmp directory and test files"
	[ -n "$FILEBACKUP" ] && rlFileRestore
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
