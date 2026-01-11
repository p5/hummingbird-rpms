#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/cracklib/Sanity/Localization
#   Description: Check if package localization is correct
#   Author: Hubert Kario <hkario@redhat.com>
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
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="cracklib"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlAssertRpm grep
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
    rlPhaseEnd


    rlPhaseStartTest "Sanity"
        rlRun "echo 'aVk(|vDTRz$xVE-W6(Z2' | LANG=C cracklib-check | grep ': OK'" 0 "Check if cracklib-check accepts complex passwords"
        rlRun "echo AAAAAAAAAAAA | LANG=C cracklib-check | grep ': OK'" 1 "Verify that cracklib-check rejects simple passwords"
        rlRun "echo AAAAAAAAAAAA | LANG=C cracklib-check | grep 'DIFFERENT'" 0 "Verify that rejection message contains string 'DIFFERENT'"
    rlPhaseEnd

NAME[0]="Assamese"
CODE[0]="as_IN.utf8"

NAME[1]="Bengali"
CODE[1]="bn_IN.utf8"

NAME[2]="German"
CODE[2]="de_DE.utf8"

NAME[3]="Spanish"
CODE[3]="es_ES.utf8"

NAME[4]="French"
CODE[4]="fr_FR.utf8"

NAME[5]="Gujarati"
CODE[5]="gu_IN.utf8"

NAME[6]="Hindi"
CODE[6]="hi_IN.utf8"

NAME[7]="Italian"
CODE[7]="it_IT.utf8"

NAME[8]="Japanese"
CODE[8]="ja_JP.utf8"

NAME[9]="Kannada"
CODE[9]="kn_IN.utf8"

NAME[10]="Korean"
CODE[10]="ko_KR.utf8"

NAME[11]="Malayalam"
CODE[11]="ml_IN.utf8"

NAME[12]="Marathi"
CODE[12]="mr_IN.utf8"

NAME[13]="Oriya"
CODE[13]="or_IN.utf8"

NAME[14]="Punjabi"
CODE[14]="pa_IN.utf8"

NAME[15]="Brazil Portugese"
CODE[15]="pt_BR.utf8"

NAME[16]="Russian"
CODE[16]="ru_RU.utf8"

NAME[17]="Tamil"
CODE[17]="ta_IN.utf8"

NAME[18]="Telugu"
CODE[18]="te_IN.utf8"

NAME[19]="Chinese"
CODE[19]="zh_CN.utf8"

NAME[20]="Taiwanese Chinese"
CODE[20]="zh_TW.utf8"

for i in ${!NAME[@]}; do
    rlPhaseStartTest "${NAME[$i]}"
        rlRun "echo AAAAAAAAAAAA | LANG=${CODE[$i]} cracklib-check | grep -Ev DIFFERENT\>" 0 "Check if fallback message isn't used"
        rlRun "echo AAAAAAAAAAAA | LANG=${CODE[$i]} cracklib-check | grep '???????'" 1 "Check if message isn't clobbered"
    rlPhaseEnd
done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
