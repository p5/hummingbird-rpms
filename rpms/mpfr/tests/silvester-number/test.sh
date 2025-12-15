#!/bin/sh -eux

OUT="$(gawk -M 'BEGIN {
  s = 2
  for (i = 1; i <= 7; i++)
    s = s * (s - 1) + 1
  print s
}')"

test "$OUT" = "113423713055421844361000443"
