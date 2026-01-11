#! /bin/bash
# ctags basics

PACKAGES="ctags"
# SERVICES=""

# source the test script helpers
# requires beakerlib package
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
	rlPhaseStartSetup
		for p in $PACKAGES ; do
			rlAssertRpm $p
		done
		rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
      rlRun "cp * $TmpDir"
		rlRun "pushd $TmpDir"
	rlPhaseEnd

	rlPhaseStartTest "Smoke, sanity and function tests"
      rlRun "ctags --version" 0 "Show version"
      rlRun "ctags --help" 0 "Show help"
      rlRun "ctags --license" 0 "Show license"
      rlRun -s "ctags --list-kinds" 0 "Output a list of all tag kinds for all languages"
      rlAssertNotDiffer ctags-kinds-list $rlRun_LOG
      rlRun -s "ctags --list-languages" 0 "Output list of supported languages"
      rlAssertNotDiffer ctags-lang-list $rlRun_LOG
      rlRun -s "ctags --list-maps" 0 "Output list of language mappings"
      rlAssertNotDiffer ctags-maps-list $rlRun_LOG
      for l in python c ; do
         rlRun "ctags -f test test.$l" 0 "Language: $l, $lWrite tags to file test"
         rlAssertExists test
         rlRun "ctags --fields=k test.%l" 0 "Language: $l, Include selected extension fields=k"
         rlRun "ctags --fields=+afmikKlnsSz test.$l" 0 "Language: $l, Check extension fields=+afmikKlnsSz"
         rlRun "ctags --extra=+fq --format=1 test.$l" 0 "Language: $l, Check options --extra=+fq --format=1"
      done
		# check man page
		rlRun "man -P head ctags" 0 "Show the ctags man page"
		# check for sane license and readme file
		rlRun "head /usr/share/licenses/ctags/COPYING" 0 "Check for license file"
	rlPhaseEnd

	rlPhaseStartCleanup
		rlRun "popd"
		rlRun "rm -fr $TmpDir" 0 "Removing tmp directory"
	rlPhaseEnd

rlJournalPrintText
rlJournalEnd
