#!/usr/bin/bash
set -e -u -o pipefail

# Allow for local testing
rargs=()
if [ -n "${MACROS_PATH:-}" ]; then
    default_macros_path="$(rpm --showrc | grep 'Macro path' | awk -F ': ' '{print $2}')"
    rargs+=("--macros" "${default_macros_path}:${MACROS_PATH}")
fi

build_rustflags="$(rpm -E '%{build_rustflags}')"
# For good measure
[ "${build_rustflags}" != "%{build_rustflags}" ]
#
flags="$(rpm "${rargs[@]}" -E '%set_build_flags')"

echo 'Check that RUSTFLAGS is set after evaluating %set_build_flags'
(
    eval "${flags}"
    # set -u will make this fail if $RUSTFLAGS isn't defined
    [ "${RUSTFLAGS}" = "${build_rustflags}" ]
)
