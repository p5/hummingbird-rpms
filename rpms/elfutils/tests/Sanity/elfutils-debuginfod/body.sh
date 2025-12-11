#!/bin/bash

set -xeo pipefail


export DEBUGINFOD_VERBOSE=1
export DEBUGINFOD_CACHE_PATH=$HOME/.debuginfod_client_cache/

# Initial cleanup
systemctl stop debuginfod
rm -rf ~/.cache/debuginfod_client
rm -rf /usr/src/my_extra_rpms $DEBUGINFOD_CACHE_PATH
mkdir $DEBUGINFOD_CACHE_PATH
journalctl -g debuginfod -f &
logger=$!

# Set up a delay.  A delay of 3 worked for me reliably for manual testing.
DELAY=120

# Clean up after possible previous failed (=> unfinished) run of this testcase
rm -rf /usr/src/my_extra_rpms $HOME/.debuginfod_client_cache

# Check the config file is there
cat /etc/sysconfig/debuginfod

# Make sure the config file doesn't contain unwanted relicts
# from possible previous failed run of this testcase
fgrep DEBUGINFOD_PATHS /etc/sysconfig/debuginfod | (! fgrep /usr/src/my_extra_rpms)

# Add some directory to the DEBUGINFOD_PATH and configure it
# within /etc/sysconfig/debuginfod
mkdir -p /usr/src/my_extra_rpms
sed -i 's/DEBUGINFOD_PATHS="[^"]*/\0\ \/usr\/src\/my_extra_rpms/' /etc/sysconfig/debuginfod
fgrep DEBUGINFOD_PATHS /etc/sysconfig/debuginfod | fgrep /usr/src/my_extra_rpms

# Note the DEBUGINFOD_PORT in the sysconfig file
# and use it to export the server URL for the client to use
source /etc/sysconfig/debuginfod
export DEBUGINFOD_URLS="localhost:$DEBUGINFOD_PORT"

# Get the build-id from some installed binary and make sure
# it isn't found
buildid=$(eu-unstrip -n -e /usr/bin/true | cut -f2 -d\ | cut -f1 -d@)
! debuginfod-find executable $buildid

# Start the service
systemctl start debuginfod

# Give it some time to index
sleep $DELAY

# Now the binary should be found
debuginfod-find executable $buildid

# Take a small debuginfo rpm and make sure you know the buildid of
# some .debug file in to the directory you created and added to
# the DEBUGINFO_PATH in the config file.
cp sshpass-debuginfo-1.09-2.fc35.x86_64.rpm /usr/src/my_extra_rpms

# Make sure the denuginfo can't be found yet
# Related:
# - https://bugzilla.redhat.com/show_bug.cgi?id=2023454
# - https://sourceware.org/bugzilla/show_bug.cgi?id=28240
! debuginfod-find debuginfo 73952ed43c6edc82cc92186a581ec27f009c529c
echo 0 > $DEBUGINFOD_CACHE_PATH/cache_miss_s

# Tell debuginfod to start indexing immediately
debuginfod_pid=$(systemctl status debuginfod | fgrep PID | grep -Po '\d+')
kill -SIGUSR1 $debuginfod_pid

# Give it some time to index
sleep $DELAY

# Try to find the debug file with the known buildid
debuginfod-find debuginfo 73952ed43c6edc82cc92186a581ec27f009c529c

# Clean up
rm -rf /usr/src/my_extra_rpms $HOME/.debuginfod_client_cache

# Kill the logger
kill $logger
