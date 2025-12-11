#!/bin/bash -ex

# Clone
rm -rf runtest.sh db tmp
git clone https://github.com/file/file-tests.git
cp -a file-tests/db .
rm -rf file-tests

blocklist="$(python3 -c 'from readfile import *; print(" ".join(main()))')"

# Prepare
printf $'#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh

compare() {
    IN="db/$1"
    OUT="$TMPDIR/out"
    ERR="$TMPDIR/err"
    rlRun "file \'$IN\' > \'$OUT\' 2> \'$ERR\'" "0" "Run file on $1"
    sed -i "s|^$IN: ||" "$OUT"
    REF="reference/$1.ref"
    if ! rlAssertNotDiffer "$REF" "$OUT"; then
        rlRun -l "diff -u \'$REF\' \'$OUT\'" 1
    fi
    rlRun "test ! -s \'$ERR\'" "0" "Check that stderr was empty"
}

PACKAGE="file"

rlJournalStart

    rlPhaseStartSetup
        rlAssertRpm "$PACKAGE"
        TMPDIR="$(mktemp -d)"
    rlPhaseEnd\n\n' > runtest.sh

(
    cd db
    for d in * ; do
        printf "    rlPhaseStartTest '%s'\n" "$d" >> ../runtest.sh
        for f in "$d"/* ; do
            if [[ ${f: -11} != ".source.txt" && "${blocklist[*]}" != *"$f"* ]]; then
                printf "        compare '%s'\n" "$f" >> ../runtest.sh
            fi
        done
        printf "    rlPhaseEnd\n\n" >> ../runtest.sh
    done
)

printf "    rlPhaseStartCleanup
        rm -rf \"\$TMPDIR\"
    rlPhaseEnd

    rlJournalPrintText
rlJournalEnd\n" >> runtest.sh

chmod +x runtest.sh
