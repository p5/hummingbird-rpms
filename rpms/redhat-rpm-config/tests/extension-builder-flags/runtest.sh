#!/bin/bash

set -ex
# Verify that the extension builder flags are stripped of non-required flags.
# The flags may appear in random order due to being accessed through a lua
# associative array.
for f in %{extension_cflags} %{extension_cxxflags} %{extension_fflags}; do
  [[ $(rpm --eval "$f") =~ ^[[:space:]]*(-fexceptions -fcf-protection|-fcf-protection -fexceptions|-fcf-protection -mbranch-protection=standard|-mbranch-protection=standard -fexceptions)[[:space:]]*$ ]]
done
# The extension ldflag should always be empty
[[ -z $(rpm --eval "%extension_ldflags") ]]
