#!/bin/bash

set -ex

# a quick PCM API test
str=$(aplay -L | grep -E "^null$")
if [ "$str" != "null" ]; then
  echo "The 'null' pcm plugin was not found!"
  exit 99
fi
