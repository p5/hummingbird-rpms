#!/bin/bash

set -eux
set -o pipefail

pushd $TMT_SOURCE_DIR/lksctp-tools-*/src/func_tests
make v4test v6test
popd
