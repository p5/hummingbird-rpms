#!/bin/bash

echo "

jpg: 364592 x
gif: 97148 x" | awk '{ if ('\!'length($3)) $3="-"; print
sprintf("%-10s%8s%10s%s", $1, $2, "", $3); }'

