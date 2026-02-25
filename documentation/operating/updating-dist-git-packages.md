# Updating Dist-git Packages

Packages are automatically updated from Fedora dist-git. Each update creates a separate MR that is automatically approved and merged when CI passes.

## Testing Locally

```bash
# Dry-run (check first 5 packages, no MRs)
./ci/dist_git_update_multi_mr.sh --clone --max=5

# Check only clean packages (skip modified/native)
./ci/dist_git_update_multi_mr.sh --clone --clean-only

# Create up to 3 test MRs (checks all packages, stops after finding 3 updates)
export CHORE_MR_GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
./ci/dist_git_update_multi_mr.sh --clone --max=3 --create-mrs

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
- `--max=N` - When creating MRs: checks packages until N updates found. When dry-run: checks first N packages
- `--create-mrs` - Actually create MRs (requires token)
- `--clean-only` - Skip packages with `modification_status` of 'modified' or 'native', only process clean packages

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

## Auto-Merge and Auto-Approval

MRs created by this script are configured to:
- **Auto-merge** when pipeline succeeds (set via `merge_request.merge_when_pipeline_succeeds`)
- **Auto-approve** after 10 minutes via the `chore_mr_approval` CI job (gives Konflux time to post commit statuses)

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
