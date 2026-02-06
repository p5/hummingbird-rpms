# Updating Dist-git Packages

Packages are automatically updated from Fedora dist-git. Each update creates a separate MR that is automatically approved and merged when CI passes.

## Testing Locally

```bash
# Dry-run (check first 5 packages, no MRs)
./ci/dist_git_update_multi_mr.sh --clone --max=5

# Create up to 3 test MRs (checks all packages, stops after finding 3 updates)
export CHORE_MR_GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
./ci/dist_git_update_multi_mr.sh --clone --max=3 --create-mrs
```

## Environment Variables

- `CHORE_MR_GITLAB_TOKEN` - GitLab token with `write_repository` scope (required for `--create-mrs`)
- `CHORE_MR_APPROVAL_GITLAB_TOKEN` - GitLab token with `api` scope for auto-approving MRs (used by CI)
- `GITLAB_REMOTE_URL` - Target repo (default: https://gitlab.com/redhat/hummingbird/rpms.git)

## Flags

- `--clone` - Clone from GitLab to /tmp (safe for local testing, uses latest main branch)
- `--max=N` - When creating MRs: checks packages until N updates found. When dry-run: checks first N packages
- `--create-mrs` - Actually create MRs (requires token)

## Auto-Merge and Auto-Approval

MRs created by this script are configured to:
- **Auto-merge** when pipeline succeeds (set via `merge_request.merge_when_pipeline_succeeds`)
- **Auto-approve** after 10 minutes via the `chore_mr_approval` CI job (gives Konflux time to post commit statuses)
