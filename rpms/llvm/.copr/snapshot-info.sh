#!/usr/bin/bash

# You need these packages to run this script: git tar xz curl-minimal

set -e

# This is important for systems that have a different local but want to produce
# a valid changelog date.
LANG=en_EN

function loginfo() {
    local msg=$1
    >&2 echo "[INFO]" $msg
}

function logerr() {
    local msg=$1
    >&2 echo "[ERROR]" $msg
}

# Check if we shall gather versioning information from a supplied git tree
if [ "$GIT_TREE" != "" ]; then
    loginfo "Gathering snapshot info from here: $GIT_TREE"
    if [ "$(git -C $GIT_TREE  rev-parse --is-inside-work-tree 2>/dev/null)" != "true" ]; then
        logerr "Not a git directory: $GIT_TREE"
        exit 1
    fi
    llvm_snapshot_git_revision=$(git -C $GIT_TREE rev-parse HEAD)
    versionfile=$GIT_TREE/cmake/Modules/LLVMVersion.cmake
    llvm_snapshot_version=`grep -ioP 'set\(\s*LLVM_VERSION_(MAJOR|MINOR|PATCH)\s\K[0-9]+' ${versionfile} | paste -sd '.'`
fi

loginfo "Determine date in YYYYMMDD form"
llvm_snapshot_yyyymmdd=$(date +%Y%m%d)
[[ ! -z "${YYYYMMDD}" ]] && llvm_snapshot_yyyymmdd=$YYYYMMDD

if [ -z $GIT_TREE ]; then
    git_revision_url=https://github.com/fedora-llvm-team/llvm-snapshots/releases/download/snapshot-version-sync/llvm-git-revision-${llvm_snapshot_yyyymmdd}.txt
    loginfo "Get the revision for today from $git_revision_url"
    llvm_snapshot_git_revision=$(curl -sL $git_revision_url)
fi
llvm_snapshot_git_revision_short=$(echo "${llvm_snapshot_git_revision:0:14}")


if [ -z $GIT_TREE ]; then
    release_url=https://github.com/fedora-llvm-team/llvm-snapshots/releases/download/snapshot-version-sync/llvm-release-${llvm_snapshot_yyyymmdd}.txt
    loginfo "Get the release for today from $release_url"
    llvm_snapshot_version=$(curl -sL $release_url)
fi
llvm_snapshot_version_major=$(echo $llvm_snapshot_version | cut -f1 -d.)
llvm_snapshot_version_minor=$(echo $llvm_snapshot_version | cut -f2 -d.)
llvm_snapshot_version_patch=$(echo $llvm_snapshot_version | cut -f3 -d.)
llvm_snapshot_version_suffix=pre${llvm_snapshot_yyyymmdd}.g${llvm_snapshot_git_revision_short}

tempfile=$(mktemp)
cat > $tempfile <<EOF
%global maj_ver ${llvm_snapshot_version_major}
%global min_ver ${llvm_snapshot_version_minor}
%global patch_ver ${llvm_snapshot_version_patch}
%undefine rc_ver

%global llvm_snapshot_version            ${llvm_snapshot_version}
%global llvm_snapshot_version_major      ${llvm_snapshot_version_major}
%global llvm_snapshot_version_minor      ${llvm_snapshot_version_minor}
%global llvm_snapshot_version_patch      ${llvm_snapshot_version_patch}
%global llvm_snapshot_yyyymmdd           ${llvm_snapshot_yyyymmdd}
%global llvm_snapshot_git_revision       ${llvm_snapshot_git_revision}
%global llvm_snapshot_git_revision_short ${llvm_snapshot_git_revision_short}
%global llvm_snapshot_version_suffix     ${llvm_snapshot_version_suffix}
EOF

# One for logs
cat $tempfile >&2

# One to redirect it away
cat $tempfile
