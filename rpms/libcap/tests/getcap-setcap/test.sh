#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest "Should set and get capabilities on multiple files"
        rlRun "touch test-file-0"
        rlRun "touch test-file-1"
        rlRun "setcap cap_net_admin+p test-file-0 cap_net_raw+ei test-file-1"
        rlRun -s "getcap test-file-0 test-file-1"
        rlAssertGrep "test-file-0.*cap_net_admin[+=]p" $rlRun_LOG -E
        rlAssertGrep "test-file-1.*cap_net_raw[+=]ei" $rlRun_LOG -E
        rlRun "rm -f test-file-0 test-file-1"
    rlPhaseEnd

    rlPhaseStartTest "Should set capabilities via stdin"
        rlRun "touch test-file-0"
        rlRun "echo -e 'cap_net_raw+p\ncap_net_admin+p' > input"
        rlRun -s "setcap - test-file-0 < input"
        rlAssertGrep "Please" $rlRun_LOG
        rlRun -s "getcap test-file-0"
        rlAssertGrep "cap_net_admin,cap_net_raw[+=]p" $rlRun_LOG -E
        rlRun "rm -f test-file-0"
    rlPhaseEnd

    rlPhaseStartTest "Should set capabilities quietly via stdin"
        rlRun "touch test-file-0"
        rlRun "echo -e 'cap_net_raw+p' > input"
        rlRun -s "setcap -q - test-file-0 < input"
        rlAssertNotGrep "Please" $rlRun_LOG
        rlRun -s "getcap test-file-0"
        rlAssertGrep "cap_net_raw[+=]p" $rlRun_LOG -E
        rlRun "rm -f test-file-0"
    rlPhaseEnd

    rlPhaseStartTest "Should remove capabilities"
        rlRun "touch test-file-0"
        rlRun "setcap cap_net_admin+p test-file-0"
        rlRun "setcap -r test-file-0"
        rlRun -s "getcap test-file-0"
        rlAssertNotGrep "cap_net_admin" $rlRun_LOG
        rlRun "rm -f test-file-0"
    rlPhaseEnd

    rlPhaseStartTest "Should list capabilities recursively"
        rlRun "touch test-file-0"
        rlRun "mkdir test-dir-1"
        rlRun "touch test-dir-1/test-file-1"
        rlRun "setcap cap_net_admin+p test-file-0 cap_net_raw+ei test-dir-1/test-file-1"
        rlRun -s "getcap -r *"
        rlAssertGrep "^test-file-0.*cap_net_admin[+=]p\$" $rlRun_LOG -E
        rlAssertGrep "^test-dir-1/test-file-1.*cap_net_raw[+=]ei\$" $rlRun_LOG -E
        rlRun "rm -f test-file-0"
        rlRun "rm -rf test-dir-1"
    rlPhaseEnd

    rlPhaseStartTest "listing capabilities verbosely"
        rlRun "touch test-file-0"
        rlRun "mkdir test-dir-1"
        rlRun "touch test-dir-1/test-file-1"
        rlRun "touch test-dir-1/test-file-2"
        rlRun "setcap cap_net_admin+p test-file-0 cap_net_raw+ei test-dir-1/test-file-1"
        rlRun -s "getcap -v -r *"
        rlAssertGrep "^test-file-0.*cap_net_admin[+=]p\$" $rlRun_LOG -E
        rlAssertGrep "^test-dir-1/test-file-1.*cap_net_raw[+=]ei\$" $rlRun_LOG -E
        rlAssertGrep "^test-dir-1/test-file-2\$" $rlRun_LOG -E
        rlRun "rm -f test-file-0"
        rlRun "rm -rf test-dir-1"
    rlPhaseEnd

    rlPhaseStartTest "Should setcap print help"
        rlRun -s "setcap -h"
        rlAssertGrep "usage" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should getcap print help"
        rlRun -s "getcap -h"
        rlAssertGrep "usage" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "setcap should exit with 1 on invalid arguments"
        rlRun -s "setcap foo bar" 1
        rlAssertGrep "Invalid" $rlRun_LOG -i
    rlPhaseEnd
    rlPhaseStartTest "getcap should exit with 1 on invalid arguments"
        rlRun -s "getcap -f oo" 1
        rlAssertGrep "Invalid" $rlRun_LOG -i
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
