#!/bin/sh -eux
rc=0
for test_exec in /usr/libexec/krb5-tests-*
do
    "$test_exec" || rc=1
done
exit $rc
