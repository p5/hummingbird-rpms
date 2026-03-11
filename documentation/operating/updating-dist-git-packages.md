# Updating Dist-git Packages

Packages are automatically updated from Fedora dist-git. Each update creates a separate MR that is automatically approved and merged when CI passes.

## Testing Locally

```bash
# Dry-run (check all packages, no MRs)
./ci/dist_git_update_multi_mr.sh --clone

# Dry-run (check first 5 packages, no MRs)
./ci/dist_git_update_multi_mr.sh --clone --max-packages=5

# Check only a specific package (for testing/debugging)
./ci/dist_git_update_multi_mr.sh --clone --only-package=libgcrypt

# Check only clean packages (skip modified/native)
./ci/dist_git_update_multi_mr.sh --clone --clean-only

# Check only modified packages (skip clean/native)
./ci/dist_git_update_multi_mr.sh --clone --modified-only

# Create up to 3 test MRs (checks all packages, stops after finding 3 updates)
export CHORE_MR_GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
./ci/dist_git_update_multi_mr.sh --clone --max-updates=3 --create-mrs

# Check first 10 packages, create up to 3 MRs
export CHORE_MR_GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
./ci/dist_git_update_multi_mr.sh --clone --max-packages=10 --max-updates=3 --create-mrs

# Create MRs only for clean packages (skip modified/native)
export CHORE_MR_GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
./ci/dist_git_update_multi_mr.sh --clone --clean-only --create-mrs
```

## Environment Variables

- `CHORE_MR_GITLAB_TOKEN` - GitLab token with `write_repository` scope (required for `--create-mrs`)
- `CHORE_MR_APPROVAL_GITLAB_TOKEN` - GitLab token with `api` scope for auto-approving MRs (used by CI)
- `GITLAB_REMOTE_URL` - Target repo (default: https://gitlab.com/redhat/hummingbird/rpms.git)

## Flags

- `--clone` - Clone from GitLab to /tmp (safe for local testing, uses latest main branch)
- `--max-packages=N` - Check only the first N packages (limits input set)
- `--max-updates=N` - Stop after finding N updates (limits output MRs created)
- `--create-mrs` - Actually create MRs (requires token)
- `--only-package=NAME` - Check only the specified package (for testing/debugging specific packages)
- `--clean-only` - Skip packages with `modification_status` of 'modified' or 'native', only process clean packages
- `--modified-only` - Skip packages with `modification_status` of 'clean' or 'native', only process modified packages (mutually exclusive with `--clean-only`)

### Using --clean-only

The `--clean-only` flag filters out packages marked as 'modified' or 'native' before attempting updates. This is useful for:

1. **Better failure detection** - Exit code 1 indicates real update failures, not expected errors from modified/native packages
2. **Cleaner output** - No error messages for packages that can't be auto-updated by design
3. **Efficient CI** - Focus on packages that should update automatically
4. **Performance** - Avoids invoking `dist_git.py` for packages that will fail

Without `--clean-only`, the script attempts to update all packages. Modified/native packages fail with:
```
ERROR: Cannot auto-update <package>
       Status: modified/native
       Reason: <reason>
       Use 'sync' to force update or 'mark-modified --clean' to allow updates
```

These expected failures can mask genuine update issues. Using `--clean-only` prevents these false failures.

### Using --modified-only

The `--modified-only` flag filters to only process packages marked as 'modified', skipping clean and native packages. This is useful for checking the merge logic, as well as getting an overview of current merge conflicts.

## Auto-Merge and Auto-Approval

MRs created by this script are configured to:
- **Auto-merge** when pipeline succeeds (set via `merge_request.merge_when_pipeline_succeeds`)
- **Auto-approve** after 10 minutes via the `chore_mr_approval` CI job (gives Konflux time to post commit statuses)

## Version-Constrained Updates

Packages with a `basename` or `track_version` field in their metadata are
version-constrained. This is used for versioned packages like `golang1.26`
that track a specific upstream version line.

### How It Works

The `basename` and `track_version` metadata fields work together across two systems:

**`dist_git.py update`** (dist-git sync from Fedora):

When `track_version` is set (e.g., `"1.26"`), the update command uses prefix matching:
- `1.26` matches `1.26`, `1.26.0`, `1.26.3` (allowed)
- `1.26` does **not** match `1.27.0`, `2.0` (skipped)

Skipped packages log a warning:
```
WARNING: Skipping golang1.26: upstream version 1.27.0 doesn't match tracked version 1.26
```

**`check_upstream_versions.py`** (release-monitoring.org checks):

When `basename` is set, Anitya is queried using the basename instead of the
package directory name. For example, `golang1.26` with `basename: "golang"`
queries Anitya for `golang`. When `track_version` is also set, the list of
upstream versions returned by Anitya is filtered to only those matching the
prefix. This means `check_upstream_versions.py check` will report `1.26.5`
as the latest version for `golang1.26` even if Anitya reports `1.27.0` as
the latest `golang` release.

### Setting Up Version Constraints

```bash
# Constrain golang1.26 to only receive 1.26.x updates
./ci/dist_git.py set-basename --name golang --track-version 1.26 golang1.26

# Remove the version constraint
./ci/dist_git.py set-basename --name golang golang1.26
```

### Behavior

- `dist_git.py`: Version constraint is checked before pre-release and Koji build checks
- `dist_git.py`: The `sync` command bypasses the version constraint (explicit force operation)
- `check_upstream_versions.py`: `basename` is used for the Anitya lookup name; `track_version` filters the returned versions
- Batch operations continue processing other packages after skipping constrained ones

## Pre-Release Version Filtering

By default, the update mechanism skips pre-release versions to prevent unstable packages from entering the repository automatically. Pre-release patterns include:

- **Tilde notation**: `5.3.0~rc1`, `2.0~beta1`, `1.0~alpha` (RPM standard)
- **Suffix notation**: `5.3.0-rc1`, `2.0.beta1`, `3.0-alpha`, `1.0.dev`
- **Development markers**: `1.5git20240101`, `2024.01.snapshot`, `1.0dev`

### Manual Override

To explicitly update to a pre-release version:

```bash
# Update single package to pre-release version
./ci/dist_git.py update --allow-prerelease package-name --skip-build-check

# Batch update allowing pre-releases
./ci/dist_git.py update --allow-prerelease --skip-build-check
```

### Behavior

- Pre-release detection occurs before Koji build checks (saves API calls)
- Skipped packages log a warning with the detected pattern
- Batch updates continue processing other packages
- The `sync` command bypasses this check (explicit force operation)
