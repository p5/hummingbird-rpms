#!/bin/bash
# Creates individual MRs for each package that needs updating from dist-git
# Each package gets its own branch and merge request for independent review
#
# Usage:
#   ./ci/dist_git_update_multi_mr.sh                      # Normal mode: check all packages, create MRs for all updates
#   ./ci/dist_git_update_multi_mr.sh --clone              # Clone to /tmp, check all packages, dry-run (no MRs)
#   ./ci/dist_git_update_multi_mr.sh --clone --max-packages=10     # Clone to /tmp, check first 10 packages, dry-run
#   ./ci/dist_git_update_multi_mr.sh --clone --max-updates=3 --create-mrs  # Clone to /tmp, check all packages, create up to 3 MRs
#   ./ci/dist_git_update_multi_mr.sh --max-updates=100            # Check all packages, create up to 100 MRs (in current repo)
#   ./ci/dist_git_update_multi_mr.sh --clean-only         # Check only clean packages (skip modified/native)
#   ./ci/dist_git_update_multi_mr.sh --modified-only      # Check only modified packages (skip clean/native)
#   ./ci/dist_git_update_multi_mr.sh --clean-only --max-updates=10     # Check clean packages, create up to 10 MRs
#   ./ci/dist_git_update_multi_mr.sh --clone --clean-only      # Clone mode, check only clean packages
#   ./ci/dist_git_update_multi_mr.sh --max-packages=50 --max-updates=10  # Check first 50 packages, create up to 10 MRs
#
# Environment variables:
#   CHORE_MR_GITLAB_TOKEN    - GitLab API token with write_repository scope (required for --create-mrs)
#   GITLAB_REMOTE_URL        - GitLab repo URL (default: https://gitlab.com/redhat/hummingbird/rpms.git)

set -euo pipefail

# Parse arguments
CLONE_MODE=false
CREATE_MRS=false
MAX_PACKAGES=0  # 0 means check all packages
MAX_UPDATES=0   # 0 means unlimited
CLEAN_ONLY=false
MODIFIED_ONLY=false
TEMP_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --clone)
            CLONE_MODE=true
            shift
            ;;
        --max-packages=*)
            MAX_PACKAGES="${1#*=}"
            if ! [[ "${MAX_PACKAGES}" =~ ^[0-9]+$ ]]; then
                echo "Error: --max-packages requires a number (e.g., --max-packages=5)"
                exit 1
            fi
            shift
            ;;
        --max-updates=*)
            MAX_UPDATES="${1#*=}"
            if ! [[ "${MAX_UPDATES}" =~ ^[0-9]+$ ]]; then
                echo "Error: --max-updates requires a number (e.g., --max-updates=10)"
                exit 1
            fi
            shift
            ;;
        --create-mrs)
            CREATE_MRS=true
            shift
            ;;
        --clean-only)
            CLEAN_ONLY=true
            shift
            ;;
        --modified-only)
            MODIFIED_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--clone] [--max-packages=N] [--max-updates=N] [--create-mrs] [--clean-only] [--modified-only]"
            exit 1
            ;;
    esac
done

# Validate mutually exclusive options
if [[ "${CLEAN_ONLY}" == true && "${MODIFIED_ONLY}" == true ]]; then
    echo "Error: --clean-only and --modified-only are mutually exclusive"
    exit 1
fi

# Configuration
TARGET_BRANCH=${CI_COMMIT_BRANCH:-${CI_DEFAULT_BRANCH:-main}}

# Cleanup function for clone mode
# shellcheck disable=SC2329  # Function is invoked via EXIT trap
cleanup() {
    if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
        echo ""
        echo "Temporary directory preserved at: ${TEMP_DIR}"
        echo "You can inspect it or delete it manually when done."
    fi
}

# Setup clone mode if requested
if [[ "${CLONE_MODE}" == true ]]; then
    trap cleanup EXIT

    TEMP_DIR=$(mktemp -d /tmp/dist-git-clone.XXXXXX)
    echo "========================================"
    echo "CLONE MODE - Working in temporary directory"
    echo "========================================"
    echo "Temp dir: ${TEMP_DIR}"
    echo ""

    # Use configurable remote URL, defaulting to the upstream canonical repo
    GITLAB_REMOTE_URL="${GITLAB_REMOTE_URL:-https://gitlab.com/redhat/hummingbird/rpms.git}"

    # Extract host and project path for constructing MR URLs later
    if [[ "${GITLAB_REMOTE_URL}" =~ ^https://([^/]+)/(.+)\.git$ ]]; then
        GITLAB_HOST="${BASH_REMATCH[1]}"
        GITLAB_PROJECT="${BASH_REMATCH[2]}"
    elif [[ "${GITLAB_REMOTE_URL}" =~ ^https://([^/]+)/(.+)$ ]]; then
        GITLAB_HOST="${BASH_REMATCH[1]}"
        GITLAB_PROJECT="${BASH_REMATCH[2]%.git}"
    fi

    echo "Cloning repository from GitLab..."
    git clone --quiet --depth 1 --single-branch --branch "${TARGET_BRANCH}" "${GITLAB_REMOTE_URL}" "${TEMP_DIR}"
    cd "${TEMP_DIR}"

    # Configure git for the cloned repo
    git config user.name "Dist-git Update (Clone Mode)"
    git config user.email "noreply@example.com"

    # If --create-mrs is set, configure credentials for pushing
    if [[ "${CREATE_MRS}" == true ]]; then
        # Check that CHORE_MR_GITLAB_TOKEN is set
        if [[ -z "${CHORE_MR_GITLAB_TOKEN:-}" ]]; then
            echo "ERROR: CHORE_MR_GITLAB_TOKEN must be set when using --create-mrs"
            echo "       Token must have write_repository scope"
            exit 1
        fi

        # Configure git credentials for pushing
        git config credential.username ignored
        git config credential.helper "!echo \"password=\$CHORE_MR_GITLAB_TOKEN\"; :"

        echo "✓ Configured GitLab authentication for pushing"
    fi

    echo "✓ Repository cloned from: ${GITLAB_REMOTE_URL}"
    echo "✓ Working directory: ${TEMP_DIR}"
    echo ""
else
    cd "$(dirname "${BASH_SOURCE[0]}")/.."

    # In production mode, extract GitLab info for MR URL tracking
    GITLAB_REMOTE_URL="${GITLAB_REMOTE_URL:-https://gitlab.com/redhat/hummingbird/rpms.git}"
    if [[ "${GITLAB_REMOTE_URL}" =~ ^https://([^/]+)/(.+)\.git$ ]]; then
        GITLAB_HOST="${BASH_REMATCH[1]}"
        GITLAB_PROJECT="${BASH_REMATCH[2]}"
    elif [[ "${GITLAB_REMOTE_URL}" =~ ^https://([^/]+)/(.+)$ ]]; then
        GITLAB_HOST="${BASH_REMATCH[1]}"
        GITLAB_PROJECT="${BASH_REMATCH[2]%.git}"
    fi
fi

# Ensure git is configured (for both clone and production mode)
if [[ -z "$(git config user.name 2>/dev/null || true)" ]]; then
    if [[ -n "${GITLAB_USER_NAME:-}" ]]; then
        git config user.name "${GITLAB_USER_NAME}"
    elif [[ "${CLONE_MODE}" == false ]]; then
        echo "Warning: git user.name not configured. Commits may fail."
    fi
fi

if [[ -z "$(git config user.email 2>/dev/null || true)" ]]; then
    if [[ -n "${GITLAB_USER_EMAIL:-}" ]]; then
        git config user.email "${GITLAB_USER_EMAIL}"
    elif [[ "${CLONE_MODE}" == false ]]; then
        echo "Warning: git user.email not configured. Commits may fail."
    fi
fi

# Additional configuration
METADATA_DIR="metadata"

# Statistics tracking
PACKAGES_UPDATED=0
UPDATE_FAILURES=0
MR_FAILURES=0
PACKAGES_SKIPPED=0
PACKAGES_SKIPPED_MODIFIED_NATIVE=0
FAILED_PACKAGES=()
CREATED_MR_URLS=()

echo "========================================"
echo "Dist-git Multi-MR Update"
echo "========================================"
if [[ "${CLONE_MODE}" == true ]]; then
    echo "Mode: CLONE"
    if [[ "${CREATE_MRS}" == true ]]; then
        echo "MRs: Will be created and pushed to GitLab"
    else
        echo "MRs: Dry-run (no MRs will be created)"
    fi
else
    echo "Mode: PRODUCTION (MRs will be created)"
fi
echo "Target branch: ${TARGET_BRANCH}"
echo ""

# Determine which packages to check
metadata_files=("${METADATA_DIR}"/*.json)
total_packages=${#metadata_files[@]}

# Apply --max-packages limit to determine input set
if [[ ${MAX_PACKAGES} -gt 0 ]]; then
    packages_to_check=("${metadata_files[@]:0:${MAX_PACKAGES}}")
    echo "Checking ${#packages_to_check[@]} of ${total_packages} packages (--max-packages=${MAX_PACKAGES})"
else
    packages_to_check=("${metadata_files[@]}")
    echo "Checking all ${total_packages} packages"
fi

# Show --max-updates limit if set
if [[ ${MAX_UPDATES} -gt 0 ]]; then
    echo "Will stop after finding ${MAX_UPDATES} updates (--max-updates=${MAX_UPDATES})"
fi
echo ""

# Pre-filter packages if --clean-only or --modified-only is set
if [[ "${CLEAN_ONLY}" == true ]]; then
    echo "Filtering for clean packages only (skipping modified/native)..."
    filtered_packages=()
    for metadata_file in "${packages_to_check[@]}"; do
        status=$(jq -r '.modification_status // "clean"' "${metadata_file}")
        if [[ "${status}" == "clean" ]]; then
            filtered_packages+=("${metadata_file}")
        else
            PACKAGES_SKIPPED_MODIFIED_NATIVE=$((PACKAGES_SKIPPED_MODIFIED_NATIVE + 1))
        fi
    done
    packages_to_check=("${filtered_packages[@]}")
    echo "After filtering: ${#packages_to_check[@]} packages to check (${PACKAGES_SKIPPED_MODIFIED_NATIVE} skipped)"
    echo ""
elif [[ "${MODIFIED_ONLY}" == true ]]; then
    echo "Filtering for modified packages only (skipping clean/native)..."
    filtered_packages=()
    for metadata_file in "${packages_to_check[@]}"; do
        status=$(jq -r '.modification_status // "clean"' "${metadata_file}")
        if [[ "${status}" == "modified" ]]; then
            filtered_packages+=("${metadata_file}")
        else
            PACKAGES_SKIPPED_MODIFIED_NATIVE=$((PACKAGES_SKIPPED_MODIFIED_NATIVE + 1))
        fi
    done
    packages_to_check=("${filtered_packages[@]}")
    echo "After filtering: ${#packages_to_check[@]} packages to check (${PACKAGES_SKIPPED_MODIFIED_NATIVE} skipped)"
    echo ""
fi

# Make sure we're on the target branch before running updates
git checkout --quiet "${TARGET_BRANCH}" 2>/dev/null || true

# Save the current commit before running updates
START_COMMIT=$(git rev-parse HEAD)

# Run dist_git.py update for each package, stopping early if we have enough updates
echo "Running dist_git.py update..."
echo ""
package_num=0
updates_found=0
for metadata_file in "${packages_to_check[@]}"; do
    package_num=$((package_num + 1))
    package=$(basename "${metadata_file}" .json)
    echo "----------------------------------------"
    echo "Package ${package_num}/${#packages_to_check[@]}: ${package}"

    # Save commit before update to detect if one was created
    COMMIT_BEFORE=$(git rev-parse HEAD)

    # Run update and capture failure without exiting (despite set -e)
    if ! ./ci/dist_git.py update "${package}" 2>&1; then
        echo "  ✗ Failed to update ${package}"
        UPDATE_FAILURES=$((UPDATE_FAILURES + 1))
        FAILED_PACKAGES+=("${package} (update failed)")
        continue
    fi

    # Check if a commit was created
    COMMIT_AFTER=$(git rev-parse HEAD)
    if [[ "${COMMIT_BEFORE}" == "${COMMIT_AFTER}" ]]; then
        echo "  ✓ Already up-to-date"
    else
        echo "  ✓ Update found"
        updates_found=$((updates_found + 1))

        # If we've found enough updates, stop checking packages
        if [[ ${MAX_UPDATES} -gt 0 && ${updates_found} -ge ${MAX_UPDATES} ]]; then
            echo ""
            echo "Found ${updates_found} updates (reached --max-updates=${MAX_UPDATES}). Stopping package checks."
            echo "Skipping remaining $((${#packages_to_check[@]} - package_num)) packages."
            break
        fi
    fi
done

echo "----------------------------------------"
echo ""

# Check how many commits were created since we started
COMMITS_CREATED=$(git rev-list --count "${START_COMMIT}..HEAD" 2>/dev/null || echo "0")

if [[ ${COMMITS_CREATED} -eq 0 ]]; then
    echo "No package updates available. All packages are up-to-date."
    exit 0
fi

echo "Found ${COMMITS_CREATED} package update(s)"
echo ""

# Get list of commit SHAs (oldest first, so we process in chronological order)
# shellcheck disable=SC2312  # Command substitution in mapfile is intentional
mapfile -t COMMIT_SHAS < <(git rev-list --reverse "${START_COMMIT}..HEAD")

# Reset main back to START_COMMIT so MR branches will have commits ahead
# (The commits are preserved in COMMIT_SHAS array)
git reset --hard "${START_COMMIT}" --quiet

# Process each commit to create individual MRs
for COMMIT_SHA in "${COMMIT_SHAS[@]}"; do
    # Get commit message and extract package name
    COMMIT_MSG=$(git log -1 --format=%s "${COMMIT_SHA}")

    # Extract package name from commit message
    # Examples: "Update bash from 5.2.0-1 to 5.3.9-1" -> extract "bash"
    #           "Sync chocolate from 10-1 to 11-1" -> extract "chocolate"
    # The pattern handles both "Update" and "Sync" verbs with "from X to Y" format
    if [[ ${COMMIT_MSG} =~ ^(Update|Sync)\ ([^\ ]+)\ from\ [^\ ]+\ to\ .* ]]; then
        PACKAGE="${BASH_REMATCH[2]}"
    else
        echo "----------------------------------------"
        echo "⚠ Skipping commit ${COMMIT_SHA:0:8}: cannot parse package name from: ${COMMIT_MSG}"
        PACKAGES_SKIPPED=$((PACKAGES_SKIPPED + 1))
        continue
    fi

    echo "----------------------------------------"
    echo "Processing: ${PACKAGE}"
    echo "  Commit: ${COMMIT_SHA:0:8}"
    echo "  Message: ${COMMIT_MSG}"

    # Create package-specific branch and MR title
    BRANCH_NAME="chore/dist-git-update-${PACKAGE}"
    MR_TITLE="chore(rpms): ${COMMIT_MSG}"

    # Create a new branch from START_COMMIT (before updates) and cherry-pick this commit
    if ! git checkout --quiet "${START_COMMIT}"; then
        echo "  ✗ Failed to checkout starting commit"
        PACKAGES_FAILED=$((PACKAGES_FAILED + 1))
        FAILED_PACKAGES+=("${PACKAGE} (checkout failed)")
        continue
    fi

    # Delete branch if it exists, then create fresh
    git branch -D "${BRANCH_NAME}" 2>/dev/null || true

    if ! git checkout -b "${BRANCH_NAME}" 2>/dev/null; then
        echo "  ✗ Failed to create branch ${BRANCH_NAME}"
        PACKAGES_FAILED=$((PACKAGES_FAILED + 1))
        FAILED_PACKAGES+=("${PACKAGE} (branch creation failed)")
        continue
    fi

    # Cherry-pick the specific commit
    if ! git cherry-pick "${COMMIT_SHA}" >/dev/null 2>&1; then
        echo "  ✗ Failed to cherry-pick commit for ${PACKAGE}"
        PACKAGES_FAILED=$((PACKAGES_FAILED + 1))
        FAILED_PACKAGES+=("${PACKAGE} (cherry-pick failed)")
        git cherry-pick --abort 2>/dev/null || true
        continue
    fi

    if [[ "${CLONE_MODE}" == true && "${CREATE_MRS}" == false ]]; then
        # Clone mode without --create-mrs: dry-run, show what would be created
        echo "  → Would create MR:"
        echo "      Branch: ${BRANCH_NAME}"
        echo "      Title: ${MR_TITLE}"
        echo "  ✓ [DRY-RUN] MR would be created for ${PACKAGE}"
        PACKAGES_UPDATED=$((PACKAGES_UPDATED + 1))
    else
        # Production mode or clone mode with --create-mrs: actually create the MR
        echo "  → Creating MR: ${MR_TITLE}"

        # Create MR for this package using existing create_mr.sh
        if ./ci/create_mr.sh --branch "${BRANCH_NAME}" --title "${MR_TITLE}" --auto-merge; then
            echo "  ✓ Created MR for ${PACKAGE}"
            PACKAGES_UPDATED=$((PACKAGES_UPDATED + 1))

            # Track MR URL if we have GitLab info
            if [[ -n "${GITLAB_HOST:-}" && -n "${GITLAB_PROJECT:-}" ]]; then
                MR_URL="https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/merge_requests?source_branch=${BRANCH_NAME}"
                CREATED_MR_URLS+=("${MR_URL}")
            fi
        else
            echo "  ✗ Failed to create MR for ${PACKAGE}"
            MR_FAILURES=$((MR_FAILURES + 1))
            FAILED_PACKAGES+=("${PACKAGE} (MR creation failed)")
        fi
    fi
done

# Return to TARGET_BRANCH
git checkout --quiet "${TARGET_BRANCH}" 2>/dev/null || true

# Print summary
echo ""
echo "========================================"
echo "Summary"
echo "========================================"
if [[ "${CLONE_MODE}" == true ]]; then
    echo "  Mode: CLONE"
    if [[ "${CREATE_MRS}" == true ]]; then
        echo "  MRs: ${PACKAGES_UPDATED} created"
    else
        echo "  MRs: Dry-run (no MRs created)"
    fi
else
    echo "  Mode: PRODUCTION"
    echo "  MRs: ${PACKAGES_UPDATED} created"
fi
echo "  Packages checked:        ${#packages_to_check[@]}"
if [[ "${CLEAN_ONLY}" == true && ${PACKAGES_SKIPPED_MODIFIED_NATIVE} -gt 0 ]]; then
    echo "  Packages skipped (modified/native): ${PACKAGES_SKIPPED_MODIFIED_NATIVE}"
elif [[ "${MODIFIED_ONLY}" == true && ${PACKAGES_SKIPPED_MODIFIED_NATIVE} -gt 0 ]]; then
    echo "  Packages skipped (clean/native): ${PACKAGES_SKIPPED_MODIFIED_NATIVE}"
fi
echo "  Updates succeeded:       $((${#packages_to_check[@]} - UPDATE_FAILURES))"
echo "  Updates failed:          ${UPDATE_FAILURES}"
echo "  Commits created:         ${COMMITS_CREATED}"
echo "  Commits skipped:         ${PACKAGES_SKIPPED}"
echo "  MR failures:             ${MR_FAILURES}"

if [[ ${#FAILED_PACKAGES[@]} -gt 0 ]]; then
    echo ""
    echo "Failed packages:"
    for failed_pkg in "${FAILED_PACKAGES[@]}"; do
        echo "  - ${failed_pkg}"
    done
fi

if [[ ${#CREATED_MR_URLS[@]} -gt 0 ]]; then
    echo ""
    echo "Created MR URLs:"
    for mr_url in "${CREATED_MR_URLS[@]}"; do
        echo "  - ${mr_url}"
    done
fi
echo "========================================"

# Exit with error if any failures occurred
# But only after processing all packages so we get maximum progress
TOTAL_FAILURES=$((UPDATE_FAILURES + MR_FAILURES))
if [[ ${TOTAL_FAILURES} -gt 0 ]]; then
    echo ""
    echo "Exiting with error due to ${TOTAL_FAILURES} failed package(s)"
    exit 1
fi

echo ""
if [[ "${CLONE_MODE}" == true ]]; then
    if [[ "${CREATE_MRS}" == true ]]; then
        echo "Clone mode with MR creation completed successfully!"
    else
        echo "Clone mode (dry-run) completed successfully!"
    fi
else
    echo "All packages processed successfully!"
fi
exit 0
