#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "useradd -m pam_cap_user"
        rlRun "useradd -m pam_cap_user2"
        rlFileBackup /etc/pam.d/su
        [ -f /etc/security/capability.conf ] && rlFileBackup /etc/security/capability.conf
        rlRun "echo -e 'cap_net_raw pam_cap_user\nnone *' > /etc/security/capability.conf"
        rlRun "sed '1 s/^/auth required pam_cap.so/' -i /etc/pam.d/su" 0 "Configure pam_cap.so in /etc/pam.d/su"
    rlPhaseEnd

    rlPhaseStartTest "Should given pam_cap_user the cap_net_raw capability"
        rlRun -s "su - pam_cap_user -c 'getpcaps \$\$'"
        rlAssertGrep ".*cap_net_raw[+=].*" $rlRun_LOG -E
    rlPhaseEnd
    rlPhaseStartTest "The user pam_cap_user2 should not have the cap_net_raw capability"
        rlRun -s "su - pam_cap_user2 -c 'getpcaps \$\$'"
        rlAssertNotGrep "cap_net_raw" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "userdel -r pam_cap_user"
        rlRun "userdel -r pam_cap_user2"
        rlFileRestore
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
