#!/bin/bash
set -ex
DIR=$(mktemp -d)
pushd "$DIR"

SRCRPM=$(rpm -q --qf '%{sourcerpm}' libmodulemd)
koji download-build -a src "$SRCRPM"
rpmdev-extract "$SRCRPM"

NAME=$(rpm -q --qf %{name} "$SRCRPM")
VERSION=$(rpm -q --qf %{version} "$SRCRPM")
pushd "${SRCRPM//.rpm}"
dnf -y builddep "$NAME".spec
fedpkg prep

meson setup -Daccept_overflowed_buildorder=true -Drpmio=enabled \
    -Dskip_introspection=false -Dtest_installed_lib=true \
    -Dwith_py2=false -Dwith_py3=true \
    ./build "${NAME}-${VERSION}-build/modulemd-${VERSION}"
ninja -C ./build
meson test -C ./build

popd

popd
rm -r "$DIR"
