#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "useradd -m libcap_tester"
    rlPhaseEnd

    rlPhaseStartTest "Should remove capability"
        rlRun -s "capsh --drop=cap_sys_admin -- -c 'getpcaps \$\$'"
        rlAssertGrep "cap_sys_admin-ep" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should prevent the use of removed capability"
        rlRun -s "capsh --drop=cap_net_raw -- -c 'ping localhost -e 0 -c 1'" 2,126 "Ping without cap_net_raw shoud fail"
        rlAssertGrep "Operation not permitted" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should set the prevailing process capabilities"
        rlRun -s "capsh --caps=cap_chown+p --print"
        rlAssertGrep "^Current:.*cap_chown[+=][ei]?p[ei]?.*" $rlRun_LOG -E
    rlPhaseEnd

    rlPhaseStartTest "Should set the inheritable set of capabilities"
        rlRun -s "capsh --inh=cap_chown --print"
        rlAssertGrep "^Current:.*cap_chown[+=][ep]?i[ep]?.*" $rlRun_LOG -E
    rlPhaseEnd

    rlPhaseStartTest "Should set and show the inheritable set of capabilities"
        rlRun -s "capsh --inh=cap_chown -- -c 'getpcaps \$\$' 2>&1"
        rlAssertGrep ".*cap_chown[+=][ep]?i[ep]?.*" $rlRun_LOG -E
    rlPhaseEnd

    rlPhaseStartTest "Should assume the identity of the user nobody"
        USERID=`id -u nobody`
        GROUPID=`id -g nobody`
        rlRun -s "capsh --user=nobody -- -c 'id'"
        rlAssertGrep "uid=$USERID(nobody) gid=$GROUPID(nobody) groups=$GROUPID(nobody)" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should assume the nobody identity with uid"
        USERID=`id -u nobody`
        rlRun -s "capsh --uid=$USERID -- -c 'id'"
        rlAssertGrep "uid=$USERID(nobody) gid=0(root) groups=0(root)" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should assume guid of nobody"
        GROUPID=`id -g nobody`
        rlRun -s "capsh --gid=$GROUPID -- -c 'id'"
        rlAssertGrep "uid=0(root) gid=$GROUPID(nobody)" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should assume the supplementary groups"
        GROUPID=`id -g nobody`
        GROUP2ID=`id -g daemon`
        rlRun -s "capsh --groups=${GROUPID},${GROUP2ID} -- -c id"
        rlAssertGrep "uid=0(root) gid=0(root) groups=0(root),${GROUP2ID}(daemon),${GROUPID}(nobody)" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should decode capabilities"
        rlRun "CODE=$( cat /proc/$$/status | awk '/CapEff/ { print $2 }' )"
        rlRun "DECODE=$( capsh --decode=$CODE | cut -d '=' -f 2 )"
        rlRun "capsh --print | grep \"$DECODE\""
    rlPhaseEnd

    rlPhaseStartTest "Should detect the existence of a capability on the system"
        rlRun "capsh --supports=cap_net_raw"
    rlPhaseEnd

    rlPhaseStartTest "Should detect the absence of a capability on the system"
        rlRun -s "capsh --supports=cap_foo_bar" 1
        rlAssertGrep "cap\[cap_foo_bar\] not recognized by library" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Should error for unsupported option"
        rlRun "capsh --foo bar" 1
    rlPhaseEnd

    rlPhaseStartTest "Should run as a regular user"
        USERID=`id -u libcap_tester`
        rlRun -s "su - libcap_tester -c 'capsh --print'"
        rlAssertGrep "Current: =\$" $rlRun_LOG -E
        rlAssertGrep "uid=$USERID(libcap_tester)" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "userdel -r libcap_tester"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
