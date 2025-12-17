#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

expected_manpages=(
    'capsh(1)'
    'libcap(3)' # there are many more but if these are present then it verifies it because of the glob install
    'libpsx(3)'
    'capability.conf(5)'
    'getcap(8)'
    'getpcaps(8)'
    'setcap(8)'
    'pam_cap(8)'
)

rlJournalStart
  for page in "${expected_manpages[@]}"; do
    rlPhaseStartTest "test ${page}"
        rlRun "man --pager=cat '${page}'"
    rlPhaseEnd
  done
  if rpm --eval '%{golang_arches}' | tr ' ' '\n' | grep -q -e "$(rpm --eval '%{_arch}')"; then
    rlPhaseStartTest 'test captree(8)'
        rlRun "man --pager=cat 'captree(8)'"
    rlPhaseEnd
  fi
rlJournalEnd
