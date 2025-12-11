#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/cyrus-sasl/Sanity/sanity-ldapdb-plugin
#   Description: The ldapdb auxprop plugin provides access to credentials stored in an LDAP server.
#   Author: David Spurek <dspurek@redhat.com>
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
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="cyrus-sasl"

PACKAGES=( "cyrus-sasl"       \
           "cyrus-sasl-devel" \
           "cyrus-sasl-ldap"  \
           "cyrus-sasl-plain" \
           "expect"           \
           "pam"              \
           "openldap"         \
           "openldap-clients" \
           "openldap-servers" \
           "cyrus-sasl-md5"   )

# else branch is also relevant for Fedora
if rlIsRHEL '<6'; then
    SERVICE_LDAP=ldap
else
    SERVICE_LDAP=slapd
fi

ldapdb_id="sasluser"
ldapdb_pw="x"

SASL_PASSWORD="x"
SASL_USER="test"

if [ "`uname -i`" = "i386" ]; then
    LIBDIR=/usr/lib
else
    LIBDIR=/usr/lib64
fi
rlIsRHEL 5 && [ "`uname -i`" = "ia64" ] &&  LIBDIR=/usr/lib

function slapd_conf {
cat >/etc/openldap/slapd.conf<<'EOF'
include         /etc/openldap/schema/core.schema
include         /etc/openldap/schema/cosine.schema
include         /etc/openldap/schema/inetorgperson.schema
include         /etc/openldap/schema/nis.schema

allow bind_v2

pidfile         /var/run/openldap/slapd.pid
argsfile        /var/run/openldap/slapd.args

database        mdb
suffix          "dc=my-domain,dc=com"
rootdn          "uid=admin,dc=my-domain,dc=com"
rootpw          x

directory       /var/lib/ldap

password-hash   {CLEARTEXT}

authz-policy to
authz-regexp
        uid=(.*),cn=.*,cn=auth
        "ldap:///dc=my-domain,dc=com??sub?(uid=$1)"

index objectClass                       eq,pres
index ou,cn,mail,surname,givenname      eq,pres,sub
index uidNumber,gidNumber,loginShell    eq,pres
index uid,memberUid                     eq,pres,sub
index nisMapName,nisMapEntry            eq,pres,sub

access to * by * write
access to * by * read
access to * by * auth

EOF
return $?
}

function data_ldif {
cat >data.ldif<<EOF
dn: dc=my-domain,dc=com
objectclass: top
objectclass: domain
dc: my-domain

dn: ou=Admins,dc=my-domain,dc=com
objectclass: top
objectclass: organizationalUnit
ou: Admins

dn: uid=$ldapdb_id,ou=People,dc=my-domain,dc=com
objectClass: person
objectClass: inetOrgPerson
userPassword: $ldapdb_pw
uid: $ldapdb_id
cn: $ldapdb_id
sn: $ldapdb_id
authzTo: ldap:///ou=People,dc=my-domain,dc=com??sub?(&(objectclass=inetOrgPerson)(uid=*))

dn: ou=People,dc=my-domain,dc=com
objectclass: top
objectclass: organizationalUnit
ou: People

dn: uid=$SASL_USER,ou=People,dc=my-domain,dc=com
objectClass: person
objectClass: inetOrgPerson
userPassword: x
uid: $SASL_USER
cn: $SASL_USER
sn: $SASL_USER
EOF
return $?
}

function sasl_client {
expect <<EOF
set timeout 30
spawn sasl2-sample-client -p 8000 -s rcmd -m PLAIN localhost
expect {
    timeout {exit 1}
    eof {exit 2}
    -nocase "please enter an authentication id:" { puts $1 ; send "$1\r"}
}
expect {
    timeout {exit 3}
    eof {exit 4}
    -nocase "please enter an authorization id:" { puts $1 ; send "$1\r"}
}
expect {
    timeout {exit 5}
    eof {exit 6}
    -nocase "Password:" { puts $2 ; send "$2\r"}
}
expect {
    timeout {exit 8}
    -nocase "successful authentication" { expect eof  ; exit 0}
    -nocase "authentication failed" {exit 9}
}
expect eof
exit 0
EOF
}

# ldapdb configuration for services, in this test for sasl2-sample-server
# configuration may be for smtpd.conf,imapd.conf instead of sample.conf
function smtpd_ldapdb {
cat >$LIBDIR/sasl2/sample.conf<<EOF
pwcheck_method: auxprop
auxprop_plugin: ldapdb
mech_list: PLAIN LOGIN CRAM-MD5 DIGEST-MD5
ldapdb_uri: ldap://localhost
ldapdb_id: $ldapdb_id
ldapdb_pw: $ldapdb_pw
ldapdb_mech: DIGEST-MD5
EOF
return $?
}


rlJournalStart
    rlPhaseStartSetup
        for P in ${PACKAGES[@]}; do rlCheckRpm $P || rlDie "Package $P is missing"; done
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"

        rlFileBackup --clean "$LIBDIR/sasl2/sample.conf"
        rlFileBackup --clean "/etc/sasldb2"

        rlRun "smtpd_ldapdb" 0

        rlServiceStop $SERVICE_LDAP

        # Back-up.
        rlFileBackup --clean /var/run/openldap
        rlFileBackup --clean /var/lib/ldap && rm -rf /var/lib/ldap/*
        rlFileBackup --clean /etc/openldap/

        rlRun "slapd_conf" 0
        rlRun "cat /etc/openldap/slapd.conf" 0
        if rlIsRHEL '>=6' || rlIsFedora '>=14'; then
            rm -rf /etc/openldap/slapd.d/*
            slaptest -f /etc/openldap/slapd.conf -F /etc/openldap/slapd.d/
        fi

        rlRun "data_ldif" 0
        rlRun "slapadd -l data.ldif" 0

        chown -R ldap:ldap /var/lib/ldap/* && chmod -R a+rx /etc/openldap/

        rlRun "restorecon -vvRF /etc/openldap/"
        rlRun "service $SERVICE_LDAP start && sleep 10" 0

    rlPhaseEnd

    rlPhaseStartTest
        rlRun "ldapsearch -LLL -H ldap://localhost -s base  -b '' -x supportedSASLMechanisms" 0
        rlRun "ldapsearch -H ldap://localhost -x -b 'dc=my-domain,dc=com' '(objectclass=*)'" 0 "Check ldap entries without SASL"

        # this two ldapwhoami commands may be used for testing purposes
        #        rlRun "ldapwhoami -U $ldapdb_id -Y digest-md5" 0
        #        rlRun "ldapwhoami -U $ldapdb_id -X u:test@localhost -Y digest-md5" 0

        # sasl sample server uses ldap sasluser as sasl bind id
        # then try search user passed to sample client in ldap database
        rlRun "sasl2-sample-server -p 8000 -s rcmd -m PLAIN &>sample_server.log &" 0
        SASL_PID=`pgrep -f "sasl2-sample-server -p 8000 -s rcmd -m PLAIN"`
        rlRun "sasl_client $SASL_USER ${SASL_PASSWORD}" 0
        rlRun "sasl_client baduser ${SASL_PASSWORD}" 9
        rlRun "kill $SASL_PID" 0 ; sleep 5
        rlRun "cat sample_server.log" 0
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "service $SERVICE_LDAP stop && sleep 10" 0
        rlFileRestore
        rlServiceRestore $SERVICE_LDAP
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
