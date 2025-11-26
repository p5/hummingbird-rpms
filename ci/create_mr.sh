#!/bin/bash

set -euo pipefail
shopt -s inherit_errexit

cd "$(dirname "${BASH_SOURCE[0]}")/.."

TARGET_BRANCH=${CI_COMMIT_BRANCH:-main}

# Parse arguments
AUTO_MERGE=

while [[ $# -gt 0 ]]; do
    case $1 in
        --branch)
            BRANCH_NAME="$2"
            shift 2
            ;;
        --title)
            MR_TITLE="$2"
            shift 2
            ;;
        --auto-merge)
            AUTO_MERGE=true
            shift
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "${BRANCH_NAME:-}" ]]; then
    echo "ERROR: --branch is required" >&2
    exit 1
fi

if [[ -z "${MR_TITLE:-}" ]]; then
    echo "ERROR: --title is required" >&2
    exit 1
fi

# Check if there are commits ahead of target branch
# (dist_git.py update already commits changes)
COMMITS_AHEAD=$(git rev-list --count "${TARGET_BRANCH}..HEAD")

if [[ ${COMMITS_AHEAD} -eq 0 ]]; then
    echo "No commits ahead of ${TARGET_BRANCH}"
    exit 0
fi

echo "${COMMITS_AHEAD} commit(s) detected, creating MR..."

# Create MR branch at current HEAD (which has the commits from dist_git.py)
git switch --quiet --force-create "${BRANCH_NAME}"

push_options=(
    --quiet
    --force-with-lease
    --push-option merge_request.create
    --push-option "merge_request.title=${MR_TITLE}"
    --push-option merge_request.remove_source_branch
)

if [[ -n ${AUTO_MERGE}  ]]; then
    push_options+=(--push-option merge_request.merge_when_pipeline_succeeds)
fi

git push "${push_options[@]}" "${REMOTE:-origin}" "${BRANCH_NAME}"

echo "SUCCESS: Created/updated MR for ${BRANCH_NAME}"
