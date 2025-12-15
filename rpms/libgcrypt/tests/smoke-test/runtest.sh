#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/libgcrypt/smoke-test
#   Description: Test calls upstream test suite.
#   Author: Ondrej Moris <omoris@redhat.com>
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

. /usr/share/beakerlib/beakerlib.sh

PACKAGE="libgcrypt"

rlJournalStart

    rlPhaseStartSetup
        rlImport distribution/fips || rlFail "FIPS library needed for some phases"
        TmpDir=`mktemp -d`
        rlAssertRpm $PACKAGE
        rlRun "rlFileBackup --clean /etc/gcrypt/fips_enabled"
        if [[ -r /etc/gcrypt/hwf.deny ]]; then
            rlRun "rlFileBackup /etc/gcrypt/hwf.deny"
            rlRun "rm -f /etc/gcrypt/hwf.deny"
        fi
        rlRun "pushd $TmpDir" 0
        rlRun "rlFetchSrcForInstalled $PACKAGE"
        rlRun "rpm -ihv `ls *.rpm`" 0
        if grep '1' /proc/sys/crypto/fips_enabled; then
            rlRun "echo '1' > /etc/gcrypt/fips_enabled" 0
        fi
    rlPhaseEnd

    rlPhaseStartTest "Package build"
        TOPDIR=`rpm --eval %_topdir`
        rlRun "pushd $TOPDIR" 0
        rlRun "rm -rf BUILD/libgcrypt-*" 0-255
        rlRun "rpmbuild -vv -bc SPECS/libgcrypt.spec" 0
        libgcrypt_dir="libgcrypt-`rpm -q --qf "%{VERSION}\n" libgcrypt | head -1`"
        if [ -d "BUILD/$libgcrypt_dir-build" ]; then
            BUILDDIR="BUILD/$libgcrypt_dir-build/$libgcrypt_dir"
        else
            BUILDDIR="BUILD/$libgcrypt_dir"
        fi
        rlRun "pushd $BUILDDIR" 0
        rlRun "fipshmac src/.libs/libgcrypt.so.??" 0
        rlRun "popd"
        rlRun "popd"
    rlPhaseEnd

    rlPhaseStartTest "Upstream testsuite"
        rlRun "pushd $TOPDIR/$BUILDDIR" 0
        exp_fails=()

        rlRun "echo 'Expecting ${#exp_fails[@]} fails'"
        exp_exitcode=0
        if [[ ${#exp_fails[@]} -gt 0 ]]; then exp_exitcode=2; fi
        rlRun "make check &> $TmpDir/make_check.out" $exp_exitcode
        rlRun "grep ^FAIL: $TmpDir/make_check.out" 0,1 "Print fails"
        if [[ ${#exp_fails[@]} -gt 0 ]]; then
            for f in $(grep '^FAIL:' $TmpDir/make_check.out | awk -F ': ' '{print $2}'); do
                if [[ "${exp_fails[@]}" =~ "$f" ]]; then
                    rlLog "$f failure is expected"
                else
                    rlFail "$f failure is not expected"
                fi
            done
        else
            rlRun "grep \"All [0-9]\+ tests passed\" $TmpDir/make_check.out" 0 \
                "All tests passed"
        fi
        rlRun "cat $TmpDir/make_check.out"
        rlRun "popd"
    rlPhaseEnd

    if ! (rlIsRHEL '<=8.4' || ([[ $fipsMode = "enabled" ]] &&  rlIsFedora '<37')); then
    # (we are ~expecting to fix HW optimization problem around Fedora-37)
    rlPhaseStartTest "Performance with HW optimizations disabled - bz1990059"
        # we are gathering more samples, so that this test is robust in shared environments
        N_SAMPLES=5
        N_MEDIAN=$(echo "$N_SAMPLES/2+1" |bc)
        HWF_DENY_FILE="/etc/gcrypt/hwf.deny"
        # Disabling via cmdline arguments would need either handpicking
        # all the algorithms (variant with ":"), or making "all" work.
        # "--disable-hwf all" does not work: https://dev.gnupg.org/T5636
        #dis_arg="--disable-hwf all"
        dis_arg=""

        for x in "cipher:aes256:CBC enc" "hash:sha256:SHA256" "mac:hmac_sha256:HMAC_SHA256"; do
            alg_type=$(echo $x |cut -d: -f1)
            algorithm=$(echo $x |cut -d: -f2)
            alg_line=$(echo $x |cut -d: -f3)
            rlRun "rm -f $algorithm.ena $algorithm.dis"
            rlLogInfo "Performance measurements started ..."
            for i in `seq 1 $N_SAMPLES`; do
                # run with HW optimizations ENAbled
                rm -f $HWF_DENY_FILE
                $TOPDIR/$BUILDDIR/tests/bench-slope $alg_type $algorithm |grep "$alg_line" >>$algorithm.ena

                # run with HW optimizations DISabled
                # this looks idiotic, but I wasn't able to make --disable-hwf work
                echo "all" >$HWF_DENY_FILE
                $TOPDIR/$BUILDDIR/tests/bench-slope $dis_arg $alg_type $algorithm |grep "$alg_line" >>$algorithm.dis
            done
            rlLogInfo "Performance measurements finished"
            rlRun "cat $algorithm.ena"
            rlRun "cat $algorithm.dis"
            dis=$(cat $algorithm.dis |cut -d'|' -f2 |awk '{ print $1 }' |sort -n |sed -n "$N_MEDIAN p")
            ena=$(cat $algorithm.ena |cut -d'|' -f2 |awk '{ print $1 }' |sort -n |sed -n "$N_MEDIAN p")
            rlRun "echo '$algorithm Time: disabled $dis enabled $ena'"
            if (( $(echo "$dis > $ena" |bc -l) )); then
                rlPass "HW optimizations work for $algorithm"
            else
                rlFail "HW optimizations DO NOT work for $algorithm"
            fi
        done
    rlPhaseEnd
    fi

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0
        rlRun "rlFileRestore"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
