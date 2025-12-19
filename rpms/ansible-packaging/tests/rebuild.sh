#!/usr/bin/bash -x
set -euo pipefail

package="${1}"

cat <<'EOF' > ~/.rpmmacros
%_topdir %(echo $HOME)/rpmbuild
%_sourcedir %(pwd)
%_srcrpmdir %(pwd)
%_rpmdir %(pwd)/rpms
EOF

mkdir -p clones
cd clones
fedpkg clone -a "${package}"
cd "${package}"
fedpkg srpm
sudo dnf builddep -y *.src.rpm
rc=0
rpmbuild --rebuild *.src.rpm | tee build.log || rc=$?

# move the results to the artifacts directory, so we can examine them
artifacts="${TEST_ARTIFACTS:-/tmp/artifacts}"
mkdir -p "${artifacts}"
mv -v *.rpm rpms/*/* build.log "${artifacts}/" || :

exit "${rc}"
