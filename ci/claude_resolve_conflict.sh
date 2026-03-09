#!/bin/bash
# Automatically resolve package conflicts using Claude AI
#
# Usage:
#   ./ci/claude_resolve_conflict.sh PACKAGENAME
#
# Checks out origin/chore/dist-git-update-PACKAGENAME and resolves conflicts

set -euo pipefail

PACKAGE_NAME="${1:-}"

if [[ -z "${PACKAGE_NAME}" ]]; then
    echo "ERROR: Package name required"
    echo "Usage: $0 PACKAGENAME"
    exit 1
fi

echo "Checking out conflict branch for ${PACKAGE_NAME}..."
git fetch origin
git checkout "origin/chore/dist-git-update-${PACKAGE_NAME}"
echo "✓ On branch chore/dist-git-update-${PACKAGE_NAME}"
echo ""

# Check for conflict markers
CONFLICT_FILES=$(git grep -l "^<<<<<<< HEAD" rpms/ 2>/dev/null || true)

if [[ -z "${CONFLICT_FILES}" ]]; then
    echo "No conflicts found in rpms/ directory"
    exit 0
fi

echo "Found conflicts in:"
echo "${CONFLICT_FILES}"
echo ""

# Invoke Claude to resolve the conflict
echo "=========================================="
echo "Invoking Claude to resolve conflicts..."
echo "=========================================="
echo ""

claude --print --dangerously-skip-permissions <<EOF
Please resolve the merge conflict for package: ${PACKAGE_NAME}

Follow the process documented in documentation/operating/package-modification-tracking.md
under "Resolving Merge Conflicts" → "Resolution Process".

Read the documentation, follow all steps (1-7), and resolve the conflict.
Do NOT push the changes - just resolve and amend the commit.

Provide a summary of:
- What conflicts you found
- How you resolved them (accepted HEAD, kept hummingbird-local, or merged both)
- What the final diff shows
- Any concerns or questions
EOF

RESOLUTION_EXIT=$?

echo ""
echo "=========================================="
if [[ ${RESOLUTION_EXIT} -eq 0 ]]; then
    echo "✓ Claude resolution complete"
else
    echo "✗ Claude resolution failed (exit code: ${RESOLUTION_EXIT})"
fi
echo "=========================================="
echo ""

if [[ ${RESOLUTION_EXIT} -eq 0 ]]; then
    echo "To review the changes:"
    echo "  git show HEAD"
    echo "  git diff HEAD~1"
    echo "  ./ci/dist_git.py diff ${PACKAGE_NAME}"
    echo ""
    echo "To push the resolution:"
    echo "  git push ${REMOTE:-origin} HEAD:chore/dist-git-update-${PACKAGE_NAME} --force-with-lease --push-option merge_request.unlabel=no-test"
fi

exit "${RESOLUTION_EXIT}"
