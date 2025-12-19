#!/bin/sh

# Not using set -e on purpose as we manually validate the exit codes to print
# useful messages.
set -u

passed=0
failed=0

rpmeval() {
  # Note: --eval needs to always be *last* here
  rpm "$@" --eval='%optflags'
}

validate() {
  ret=$?
  if [ $ret -eq 0 ]; then
    echo "PASS: $*"
    passed=$((passed+1))
  else
    echo "FAIL: $*"
    failed=$((failed+1))
  fi
}

for arch in aarch64 x86_64 riscv64; do
  case "$arch" in
    x86_64|aarch64)
      flags='-fno-omit-frame-pointer -mno-omit-leaf-frame-pointer'
      ;;
    *)
      flags='-fno-omit-frame-pointer'
      ;;
  esac

  rpmeval --target="${arch}-linux" --define='_include_frame_pointers 1' | grep -q -- "$flags"
  validate "[${arch}] Test that the flags are included if the macro is defined"

  rpmeval --target="${arch}-linux" --undefine='_include_frame_pointers' | grep -qv -- "$flags"
  validate "[${arch}] Test that the flags are _not_ included if the macro is undefined"

  rpmeval --target="${arch}-linux" --define='fedora 1' | grep -q -- "$flags"
  validate "[${arch}] Test that the flags are included by default on Fedora"

  rpmeval --target="${arch}-linux" --define='rhel 1' | grep -qv -- "$flags"
  validate "[${arch}] Test that the flags are _not_ included by default on RHEL"
done

flags='-fno-omit-frame-pointer'
for arch in i386 i486 i586 i686 athlon ppc64le s390x; do
  rpmeval --target="${arch}-linux" --define='_include_frame_pointers 1' | grep -qv -- "$flags"
  validate "[${arch}] Test that the flags are not included if the macro is defined"

  rpmeval --target="${arch}-linux" | grep -qv -- "$flags"
  validate "[${arch}] Test that the flags are not included by default"
done

echo
echo "${passed} passed, ${failed} failed"

exit "$failed"
