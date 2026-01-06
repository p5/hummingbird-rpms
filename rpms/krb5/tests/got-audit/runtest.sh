#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/openssh/Sanity/got-audit
#   Description: Check pointers in the server process GOT for signs of tampering
#   Author: Gordon Messmer <gordon.messmer@gmail.com>
#

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

krb5REALM1='TEST1.REDHAT.COM'
krb5HostName=`hostname`
krb5DomainName=`hostname -d`
krb5User='alice'
krb5UserPass='alice'
krb5UserKrbPass='aaa'
krb5User2='bob'
krb5User3='carl'
krb5KDCPass='qwe'
krb5RootPass='rrr'

krb5conf="/etc/krb5.conf"
krb5confdir="/etc/krb5.conf.d"
krb5kdcconf="/var/kerberos/krb5kdc/kdc.conf"
krb5kadmacl="/var/kerberos/krb5kdc/kadm5.acl"

rlJournalStart
    rlPhaseStartSetup
        rlServiceStart sshd
        rlRun "TestDir=\$(pwd)"
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "auditfile=\$(mktemp --tmpdir=${TmpDir})"
    rlPhaseEnd

    rlPhaseStartSetup "KDC and kadmind setup"
        # Stop and backup
        rlRun "rlServiceStop kadmin krb5kdc"
        rlRun "rm -f /var/kerberos/krb5kdc/principal* /var/kerberos/krb5kdc/.k5*"
        rlFileBackup $krb5conf /var/kerberos/krb5kdc /etc/sysconfig/{kadmin,krb5kdc} /etc/hosts
        rlFileBackup --clean /root/.k5login
        [ -e /etc/krb5.keytab ] && rlFileBackup /etc/krb5.keytab
        [ -e $krb5confdir ] && rlFileBackup $krb5confdir
        # Basic setup of KDC and krb5.conf
        rlRun "sed -i \"s/\[libdefaults\]/[libdefaults]\n default_realm = $krb5REALM1/\" $krb5conf"
        rlRun "sed -i \"s/\[realms\]/[realms]\n $krb5REALM1 = {\n  kdc = $krb5HostName\n  admin_server = $krb5HostName\n }/\" $krb5conf"
        if [ "$krb5DomainName" ]; then
            rlRun "sed -i \"s/\[domain_realm\]/[domain_realm]\n .$krb5DomainName = $krb5REALM1\n $krb5DomainName = $krb5REALM1/\" $krb5conf"
        else
            rlRun "sed -i \"s/\[domain_realm\]/[domain_realm]\n $krb5HostName = $krb5REALM1/\" $krb5conf"
        fi
        rlRun "sed -i s/EXAMPLE.COM/$krb5REALM1/ $krb5kdcconf"
        # Configure the kadmin ACL
        rlRun "echo \"*/master@$krb5REALM1  *\" > $krb5kadmacl"
        if rlIsFedora '>=31';then
            rlLog "Modify supported_enctypes for Fedora >=31. Remove *DES ciphers."
            rlRun "sed -i \"s/supported_enctypes.*/supported_enctypes = aes256-cts:normal aes128-cts:normal arcfour-hmac:normal camellia256-cts:normal camellia128-cts:normal/\" /var/kerberos/krb5kdc/kdc.conf"
        elif rlIsRHEL '8' && [ `rpm -q --qf '%{VERSION}' krb5-server | cut -d"." -f2` -lt 18 ];then
            rlLog "Modify supported_enctypes for RHEL-8."
            rlRun "sed -i \"s/supported_enctypes.*/supported_enctypes = aes256-cts:normal aes128-cts:normal des3-hmac-sha1:normal arcfour-hmac:normal camellia256-cts:normal camellia128-cts:normal/\" /var/kerberos/krb5kdc/kdc.conf"
        else
            #RHEL-8 Bug 1802334 - [Rebase] krb5: rebase to 1.18:
            #- Removal of *DES encryption types
            #https://bugzilla.redhat.com/show_bug.cgi?id=1802334
            rlLog "Modify supported_enctypes for RHEL-8 with krb-1.18. Remove *DES ciphers."
            rlRun "sed -i \"s/supported_enctypes.*/supported_enctypes = aes256-cts:normal aes128-cts:normal arcfour-hmac:normal camellia256-cts:normal camellia128-cts:normal/\" /var/kerberos/krb5kdc/kdc.conf"
        fi
        # Create the realm databases
        rlRun "rngd -r /dev/urandom"
        rlRun "kdb5_util create -s -r $krb5REALM1 -P $krb5KDCPass"
        rlRun "rlServiceStart kadmin krb5kdc"
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -pw $krb5RootPass root/master\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -pw $krb5UserKrbPass $krb5User\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -randkey host/$krb5HostName\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"ktadd host/$krb5HostName\""
        # Create test system user 
        [ $krb5User != "root" ] && rlRun "useradd $krb5User"
        rlRun "echo $krb5UserPass | passwd --stdin $krb5User"
    rlPhaseEnd

    rlPhaseStartTest "Run GEF got-audit"
        rlRun "systemctl restart krb5kdc.service"
        rlRun "systemctl restart kadmin.service"
        rlRun "systemctl --no-pager status krb5kdc.service"
        rlRun "systemctl --no-pager status kadmin.service"

        rlRun "SERVICE_PID=\$( systemctl show --property=MainPID krb5kdc.service | cut -f2 -d= )"
        rlRun "echo SERVICE_PID is '$SERVICE_PID'"
        [ -n "$SERVICE_PID" ] || rlFail "No service pid was found"
        rlRun "gdb-gef --pid '$SERVICE_PID' --command='$TestDir'/got-audit.gdb --batch > '$auditfile'"
        # Basic test: ensure that at least one symbol is found in libc.so,
        #  to verify that the report looks plausible.
        rlAssertGrep " : /.*/libc.so" "$auditfile"
        # Ensure the got-audit did not report any errors
        rlAssertNotGrep " :: ERROR" "$auditfile"
        rlRun "cp '$auditfile' '$TMT_TEST_DATA'/krb5kdc-got-audit.txt"

        rlRun "SERVICE_PID=\$( systemctl show --property=MainPID kadmin.service | cut -f2 -d= )"
        rlRun "echo SERVICE_PID is '$SERVICE_PID'"
        [ -n "$SERVICE_PID" ] || rlFail "No service pid was found"
        rlRun "gdb-gef --pid '$SERVICE_PID' --command='$TestDir'/got-audit.gdb --batch > '$auditfile'"
        # Basic test: ensure that at least one symbol is found in libc.so,
        #  to verify that the report looks plausible.
        rlAssertGrep " : /.*/libc.so" "$auditfile"
        # Ensure the got-audit did not report any errors
        rlAssertNotGrep " :: ERROR" "$auditfile"
        rlRun "cp '$auditfile' '$TMT_TEST_DATA'/kadmin-got-audit.txt"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf /var/kerberos/krb5kdc/* /var/kerberos/krb5kdc/.k5* /etc/krb5* /etc/sysconfig/{kadmin,krb5kdc}"
        rlFileRestore
        rlServiceRestore krb5kdc kadmin
        [ $krb5User != "root" ] && rlRun "userdel -r -f $krb5User"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
