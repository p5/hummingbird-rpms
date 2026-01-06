#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/krb5/Sanity/inplace-upgrade-sanity-test
#   Description: Verifies basic scenarios which should work after inplace upgrade.
#   Author: Patrik Kis <pkis@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2014 Red Hat, Inc.
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
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="krb5"
PACKAGES="krb5-libs krb5-server krb5-workstation openssh"

TEST_ENTROPY_SOURCE=${TEST_ENTROPY_SOURCE:-no}
echo TEST_ENTROPY_SOURCE=$TEST_ENTROPY_SOURCE

krb5REALM1='TEST1.REDHAT.COM'
krb5REALM2='TEST2.REDHAT.COM'
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
        for pkg in $PACKAGES; do
            rlAssertRpm $pkg
        done
        rlRun "TmpDir=\$(mktemp -d)"
        rlRun "pushd $TmpDir"
        echo "-----/etc/krb5.conf----"; cat /etc/krb5.conf
        echo "-----/var/kerberos/krb5kdc/kdc.conf-----"; cat /var/kerberos/krb5kdc/kdc.conf
    rlPhaseEnd

    # Run this part on OLD and in "normal" mode
    if [[ -z $IN_PLACE_UPGRADE || $IN_PLACE_UPGRADE == old ]]; then
    rlPhaseStartSetup "KDC and kadmind setup"
        # Stop and backup
        rlRun "rlServiceStop kadmin krb5kdc"
        rlRun "rm -f /var/kerberos/krb5kdc/principal* /var/kerberos/krb5kdc/.k5*"
        rlFileBackup $krb5conf /var/kerberos/krb5kdc /etc/sysconfig/{kadmin,krb5kdc} /etc/hosts
        rlFileBackup --clean /root/.k5login
        [ -e /etc/krb5.keytab ] && rlFileBackup /etc/krb5.keytab
        [ -e $krb5confdir ] && rlFileBackup $krb5confdir
        # Make sure IPv4 is used for ssh connection
        if ! grep `hostname` /etc/hosts; then
            DEF_DEV=`ip route |grep default |awk '{print $5}'`
            echo DEF_DEV=$DEF_DEV
            DEF_IP=`ip -o -4 addr show dev $DEF_DEV |awk '{print $4}' |grep -v '/32' |sed 's|/.*||'`
            echo DEF_IP=$DEF_IP
            rlRun "echo '$DEF_IP `hostname`' >>/etc/hosts"
            grep `hostname` /etc/hosts
        fi
        # Basic setup of KDC and krb5.conf
        if rlIsRHEL 6; then
            rlRun "sed -i \"s/EXAMPLE.COM/$krb5REALM1/\" $krb5conf"
            rlRun "sed -i \"s/kerberos.example.com/$krb5HostName/\" $krb5conf"
            if [ "$krb5DomainName" ]; then
                rlRun "sed -i \"s/example.com/$krb5DomainName/\" $krb5conf"
            fi
        else
            rlRun "sed -i \"s/\[libdefaults\]/[libdefaults]\n default_realm = $krb5REALM1/\" $krb5conf"
            rlRun "sed -i \"s/\[realms\]/[realms]\n $krb5REALM1 = {\n  kdc = $krb5HostName\n  admin_server = $krb5HostName\n }/\" $krb5conf"
            if [ "$krb5DomainName" ]; then
                rlRun "sed -i \"s/\[domain_realm\]/[domain_realm]\n .$krb5DomainName = $krb5REALM1\n $krb5DomainName = $krb5REALM1/\" $krb5conf"
            else
                rlRun "sed -i \"s/\[domain_realm\]/[domain_realm]\n $krb5HostName = $krb5REALM1/\" $krb5conf"
            fi
        fi
        rlRun "sed -i s/EXAMPLE.COM/$krb5REALM1/ $krb5kdcconf"
        # Configure the kadmin ACL
        rlRun "echo \"*/master@$krb5REALM1  *\" > $krb5kadmacl"
        # Configure the 2nd realmd
        cat >>$krb5kdcconf <<_EOF

 $krb5REALM2 = {
  #master_key_type = aes256-cts
  database_name = /var/kerberos/krb5kdc/principal.$krb5REALM1
  acl_file = /var/kerberos/krb5kdc/kadm5.acl
  dict_file = /usr/share/dict/words
  admin_keytab = /var/kerberos/krb5kdc/kadm5.keytab
  supported_enctypes = aes256-cts:normal aes128-cts:normal des3-hmac-sha1:normal arcfour-hmac:normal des-hmac-sha1:normal des-cbc-md5:normal des-cbc-crc:normal
}
_EOF
        

if rlIsRHEL '7'; then
    rlLog "Modify supported_enctypes for RHEL-7."
    rlRun "sed -i \"s/supported_enctypes.*/supported_enctypes = aes256-cts:normal aes128-cts:normal des3-hmac-sha1:normal arcfour-hmac:normal camellia256-cts:normal camellia128-cts:normal des-hmac-sha1:normal des-cbc-md5:normal des-cbc-crc:normal/\" /var/kerberos/krb5kdc/kdc.conf"
    # Remove 3DES and DES cipher suite from kdc.conf - Fedora 31
    # Fedora 31 - krb5 will be removing support for DES, 3DES, and crc-32 entirely
    # they will not be allowed in session keys or long-term keys. (BZ#1670398)
    # https://fedoraproject.org/wiki/Changes/krb5_crypto_modernization
elif rlIsFedora '>=31';then
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
        rlRun "sed -i \"s/\[realms\]/[realms]\n $krb5REALM2 = {\n  kdc = $krb5HostName\n  admin_server = $krb5HostName\n }/\" $krb5conf"
    cat >> $krb5conf << _EOF

[capaths]
 $krb5REALM1 = {
  $krb5REALM2 = .
 }
_EOF
        # BZ#1394908: Test the entropy source (not relevant for RHEL6)
        if ! rlIsRHEL 6 && [[ $TEST_ENTROPY_SOURCE == 'yes' ]]; then
            rlLog "BZ#1394908: The source of entropy will be tested as well"
            # Check number of audit rules
            number_rules=$(auditctl -l | grep -v "No rules" | wc -l)
            if [[ ${number_rules} -ne 0 ]];then
                truncate -s0 /var/log/audit/audit.log
                rlRun "auditctl -D" 0 "Delete previous audit rules"
            fi
            START_DATE=`date +%H:%M:%S`
            echo START_DATE=$START_DATE
            sleep 1
            rlRun "auditctl -w /dev/random -p rwxa -k RAND"
            auditctl -l
            sleep 5
            rlRun "ausearch -i -k RAND -ts $START_DATE"
        fi
        
        echo "-----/etc/krb5.conf----"; cat /etc/krb5.conf
        echo "-----/var/kerberos/krb5kdc/kdc.conf-----"; cat /var/kerberos/krb5kdc/kdc.conf

        # Create the realm databases
        rlRun "rngd -r /dev/urandom"
        rlRun "kdb5_util create -s -r $krb5REALM1 -P $krb5KDCPass"
        rlRun "kdb5_util create -s -r $krb5REALM2 -P $krb5KDCPass"
        # Configure KDC to handle 2 realms
        if rlIsRHEL 6; then
            rlRun "echo \"KRB5REALM=$krb5REALM1\" > /etc/sysconfig/krb5kdc"
            rlRun "echo KRB5KDC_ARGS=\\\"-r $krb5REALM2\\\" >> /etc/sysconfig/krb5kdc"
        else
            rlRun "echo KRB5KDC_ARGS=\\\"-r $krb5REALM1 -r $krb5REALM2 \\\" >/etc/sysconfig/krb5kdc"
        fi
        rlRun "rlServiceStart kadmin krb5kdc"
        # Add krb5 principals for the 2nd realm
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -pw $krb5RootPass root/master\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -pw $krb5UserKrbPass $krb5User\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -randkey host/$krb5HostName\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"ktadd host/$krb5HostName\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -pw $krb5KDCPass krbtgt/$krb5REALM1@$krb5REALM2\""
        rlRun "kadmin.local -r $krb5REALM1 -q \"addprinc -pw $krb5KDCPass krbtgt/$krb5REALM2@$krb5REALM1\""
        # Add krb5 principals for the 2nd realm
        rlRun "kadmin.local -r $krb5REALM2 -q \"addprinc -pw $krb5UserKrbPass $krb5User2\""
        rlRun "kadmin.local -r $krb5REALM2 -q \"addprinc -randkey host/$krb5HostName\""
        rlRun "kadmin.local -r $krb5REALM2 -q \"addprinc -pw $krb5KDCPass krbtgt/$krb5REALM1@$krb5REALM2\""
        rlRun "kadmin.local -r $krb5REALM2 -q \"addprinc -pw $krb5KDCPass krbtgt/$krb5REALM2@$krb5REALM1\""
        # Create test system user 
        [ $krb5User != "root" ] && rlRun "useradd $krb5User"
        rlRun "echo $krb5UserPass | passwd --stdin $krb5User"
    rlPhaseEnd
    fi
    
    rlPhaseStartTest "Daemon start and log file test"
        # Make sure there is enough entropy and start recording of the logs
        rlRun "rngd -r /dev/urandom"
        if grep -q krb5kdc /var/log/krb5kdc.log; then
            tail -n0 -f /var/log/krb5kdc.log &> krb5kdc.log.record &
            KRB5KDC_LOG_PID=$!
            echo "log_record_start: PID = $KRB5KDC_LOG_PID"
            sleep 1
        elif journalctl |grep -q krb5kdc; then
            journalctl -f &> krb5kdc.log.record &
            KRB5KDC_LOG_PID=$!
            echo "log_record_start: PID = $KRB5KDC_LOG_PID"
            sleep 1
        else
            rlFail "Could not find krb5kdc logs"
            echo "journalctl:"
            journalctl -n 100
            ls -la /var/log/krb5kdc*
            echo "/var/log/krb5kdc.log:"
            tail -n 100 /var/log/krb5kdc.log
        fi
        if grep -q kadmind /var/log/kadmind.log; then
            tail -n0 -f /var/log/kadmind.log &> kadmind.log.record &
            KADMIND_LOG_PID=$!
            echo "log_record_start: PID = $KADMIND_LOG_PID"
            sleep 1
        elif journalctl |grep -q kadmind; then
            journalctl -f &> kadmind.log.record &
            KADMIND_LOG_PID=$!
            echo "log_record_start: PID = $KADMIND_LOG_PID"
            sleep 1
        else
            rlFail "Could not find kadmind logs"
            echo "journalctl:"
            journalctl -n 100
            ls -la /var/log/kadmind*
            echo "/var/log/kadmind.log:"
            tail -n 100 /var/log/kadmind.log
        fi

        #add 'list' privilege for root/master 
        sed -i -e '$a*/master@EXAMPLE.COM    *' /var/kerberos/krb5kdc/kadm5.acl

        # Restart daemon auto start
        if rlIsRHEL 6; then
            rlRun "service krb5kdc restart"
            rlRun "service kadmin restart"
            rlRun "service krb5kdc status"
            rlRun "service kadmin status"
        else
            rlRun "systemctl restart krb5kdc.service"
            rlRun "systemctl restart kadmin.service"
            rlRun "systemctl --no-pager status krb5kdc.service"
            rlRun "systemctl --no-pager status kadmin.service"
        fi
        rlRun "echo $krb5UserKrbPass |kinit $krb5User && klist"
        rlRun "kdestroy"
        rlRun "kadmin -p root/master -w rrr -q 'getprincs'"
        rlAssertGrep "AS_REQ.*$krb5User@$krb5REALM1.*krbtgt/$krb5REALM1@$krb5REALM1" krb5kdc.log.record

#The principal related to kadmin are not created with hostname (kadmin/hostname@REALM) during creating krb5 DB
#RHEL9 constains only kadmin/admin@REALM - this change was intentional - Don't create hostbased principals in new KDBs
#https://krbdev.mit.edu/rt/Ticket/Display.html?id=8935
        if rlIsRHEL 9 || rlIsFedora '>=33';then
           kadmin_princ="Request: kadm5_init.*root/master@$krb5REALM1.*service=kadmin/admin@$krb5REALM1"
        else
           kadmin_princ="Request: kadm5_init.*root/master@$krb5REALM1.*service=kadmin/.*`hostname`@$krb5REALM1"
        fi
        rlAssertGrep "${kadmin_princ}" kadmind.log.record
        #rlAssertGrep "Request: kadm5_init.*root\/master@$krb5REALM1.*service=kadmin\/(admin|.*`hostname`)@$krb5REALM1" kadmind.log.record -E
        echo "***krb5kdc.log.record***" && cat krb5kdc.log.record
        echo "***kadmind.log.record***" && cat kadmind.log.record
        # Stop log recording
        kill $KADMIND_LOG_PID
        kill $KRB5KDC_LOG_PID
    rlPhaseEnd

    rlPhaseStartTest "SSH test"
        cat > sshtest.exp <<'_EOF'
#!/usr/bin/expect -f
set USER    [lindex $argv 0]
set HOST    [lindex $argv 1]
set timeout 15
spawn ssh $USER@$HOST pwd
expect {
    -re ".*(yes/no).*" { send -- "yes\r"; exp_continue }
    -re ".*password:.*" { exit 1 }
    "/home/$USER" { exit 0 }
    timeout { exit 2 }
    eof { exit 3 }
}
exit 4
_EOF
        chmod 744 sshtest.exp
        rlAssertExists sshtest.exp
        rlRun "echo $krb5UserKrbPass |kinit $krb5User && klist"
        rlRun "./sshtest.exp $krb5User $krb5HostName"; echo
        rlRun "klist &>klist.log"
        cat klist.log
        rlAssertGrep "host/`hostname`@$krb5REALM1" klist.log
        rlRun "kdestroy"
        #BZ1841488-sshd cannot write into reply cache (/var/tmp/krb5_0.rcache2) due to security context
        #The problem is that this file had security context: system_u:object_r:kadmind_tmp_t:s0. 
        #This is a problem when the ssh via krb5-GSSAPI is used because sshd service cannot write into this file.
        if rlIsRHEL '>=8.3' || rlIsFedora '>=32'; then
            rlLog "BZ1841488-sshd cannot write into reply cache (/var/tmp/krb5_0.rcache2) due to security context"
            rlRun "sesearch -s sshd_t -t kadmind_tmp_t -c file -p write --allow | grep ^allow"
        fi
    rlPhaseEnd

    rlPhaseStartTest "Basic kadmin and kpasswd test"
        rlRun "kadmin.local -q \"listprincs\" |grep -v Authenticating >lplocal"
        rlRun "kadmin -p root/master -w $krb5RootPass -q \"listprincs\" |grep -v Authenticating >lpremote"
        rlAssertNotDiffer lplocal lpremote || diff -u lplocal lpremote
        diff lplocal lpremote
        rlRun "kadmin -p root/master -w $krb5RootPass -q \"addprinc -pw $krb5User2 $krb5User2@$krb5REALM1\""
        rlRun "kadmin -p root/master -w $krb5RootPass -q \"listprincs\" | grep \"$krb5User2@$krb5REALM1\""

        rlRun "echo $krb5User2 | kinit $krb5User2"
        rlRun "echo -e \"$krb5User2\nqwerty\nqwerty\" | kpasswd &>kpasswd.log"
        cat kpasswd.log
        rlAssertGrep "Password changed." kpasswd.log
        rlRun "echo qwerty | kinit $krb5User2"
        rlRun "kdestroy"
        rlRun "kadmin -p root/master -w $krb5RootPass -q \"delprinc -force $krb5User2@$krb5REALM1\""
    rlPhaseEnd

    rlPhaseStartTest "Basic ksu test"
        [[ -f /root/.k5login ]] && rlRun "mv /root/.k5login ."
        rlRun "echo $krb5User@$krb5REALM1 > /root/.k5login"
        rlRun "su - $krb5User -c \"echo $krb5UserKrbPass | kinit $krb5User\""
        rlRun "su - $krb5User -c \"ksu -e /usr/bin/id\" &> ksu.log"
        cat ksu.log
        rlAssertGrep "^uid=0(root) gid=0(root)" ksu.log
        rlRun "su - $krb5User -c kdestroy"
        [[ -f .k5login ]] && rlRun "mv .k5login /root/.k5login"
    rlPhaseEnd

    rlPhaseStartTest "Cross realm test"
        rlRun "echo $krb5UserKrbPass |kinit $krb5User && klist"
        rlRun "kvno host/`hostname`@$krb5REALM2"
        rlRun "klist &>klist.log"
        cat klist.log
        rlAssertGrep "krbtgt/$krb5REALM1@$krb5REALM1" klist.log
        rlAssertGrep "krbtgt/$krb5REALM2@$krb5REALM1" klist.log
        rlAssertGrep "host/`hostname`@$krb5REALM2" klist.log
        rlRun "kdestroy"
    rlPhaseEnd

    # BZ#1394908: Test the entropy source (not relevant for RHEL6)
    if ! rlIsRHEL 6 && [[ $TEST_ENTROPY_SOURCE == 'yes' ]]; then
        rlPhaseStartTest "BZ#1394908: Enable faster getrandom-based entropy system"
            echo START_DATE=$START_DATE
            auditctl -l
            sleep 5 
            rlRun "ausearch -i -k RAND -ts $START_DATE"
            rlRun "ausearch -i -k RAND -ts $START_DATE |grep comm= | grep -v comm=auditctl |grep -v 'comm=rngd'" 1
            rlRun "auditctl -D"
        rlPhaseEnd
    fi

    # Run this part on "normal" mode; in inplace upgrade no cleanup is needed
    if [[ -z $IN_PLACE_UPGRADE ]]; then
    rlPhaseStartCleanup "KDC and kadmind cleanup"
        rlRun "rm -rf /var/kerberos/krb5kdc/* /var/kerberos/krb5kdc/.k5* /etc/krb5* /etc/sysconfig/{kadmin,krb5kdc}"
        rlFileRestore
        rlRun "rlServiceRestore krb5kdc kadmin"
        [ $krb5User != "root" ] && rlRun "userdel -r -f $krb5User"
    rlPhaseEnd
    fi
    
    rlPhaseStartCleanup
        rlRun "kdestroy -A"
        rlRun "popd"
        rlRun "rm -r $TmpDir"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
