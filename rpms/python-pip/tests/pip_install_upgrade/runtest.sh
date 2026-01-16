#!/bin/sh -eux
# This script requires root privileges and you should never run it on your own machine
test $EUID -eq 0

PYTHON_VERSION=$(/usr/bin/python3 -c 'import sys; print("{}.{}".format(*sys.version_info))')
RPM_SITELIB="/usr/lib/python${PYTHON_VERSION}/site-packages"
LOCAL_SITELIB="/usr/local/lib/python${PYTHON_VERSION}/site-packages"
USER_SITELIB="/home/fedora-test-user/.local/lib/python${PYTHON_VERSION}/site-packages"

# First, let's install older Pello with pip as if it was installed by RPM
# This is an approximation, but it usually works
RPM_BUILD_ROOT=/ /usr/bin/pip install 'Pello==1.0.1'

# Now, we'll upgrade it with regular pip
/usr/bin/pip install --upgrade 'Pello==1.0.2'

# pip should see it
/usr/bin/pip freeze | grep '^Pello==1\.0\.2$'

# Both installations should still exist
test -d "${RPM_SITELIB}/pello-1.0.1.dist-info"
test -d "${LOCAL_SITELIB}/Pello-1.0.2.dist-info"

# Let's ditch the local one
/usr/bin/pip uninstall --yes Pello

# It should only remove one of them
test -d "${RPM_SITELIB}/pello-1.0.1.dist-info"
! test -d "${LOCAL_SITELIB}/Pello-1.0.2.dist-info"

# And pip should still see the RPM-installed one
/usr/bin/pip freeze | grep '^Pello==1\.0\.1$'

# Again, but as regular user
useradd fedora-test-user
su fedora-test-user -c '/usr/bin/pip install "Pello==1.0.2"'
test -d "${USER_SITELIB}/Pello-1.0.2.dist-info"
su fedora-test-user -c '/usr/bin/pip freeze' | grep '^Pello==1\.0\.2$'
su fedora-test-user -c '/usr/bin/pip uninstall --yes Pello'
su fedora-test-user -c '/usr/bin/pip freeze' | grep '^Pello==1\.0\.1$'
