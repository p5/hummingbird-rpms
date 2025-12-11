#!/bin/bash

RETVAL=0
OUT=$(mktemp)
eu-stack -p $$ |& tee $OUT
grep -i 'operation not permitted' $OUT && RETVAL=1
rm $OUT
exit $RETVAL
