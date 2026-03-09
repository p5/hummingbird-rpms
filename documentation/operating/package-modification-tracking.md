---
title: Package Modification Tracking
weight: 55
aliases: [/l/package-modification-tracking]
---

## Overview

The RPMs repository tracks whether packages have been locally modified from their
Fedora upstream source. This tracking prevents automatic updates from overwriting
local changes like backported patches or custom modifications.

## Modification Status Types

Each package metadata file (`metadata/<package>.json`) contains a `modification_status`
field with one of three values:

| Status     | Meaning                                    | Auto-updates |
|------------|--------------------------------------------|--------------|
| `clean`    | Unmodified Fedora import                   | ✅ Allowed   |
| `modified` | Local changes (patches, spec modifications)| ❌ Blocked   |
| `native`   | Hummingbird-native package (not from Fedora)| ❌ Blocked  |

An optional `track_upstream` boolean field controls whether a package is
checked by `check_upstream_versions.py` for new upstream releases (via
release-monitoring.org). The `check` subcommand only checks packages with
`"track_upstream": true` when no explicit package arguments are given. The
`list` subcommand shows all packages regardless of this field.

## Checking Package Status

View a package's modification status:

```bash
jq .modification_status metadata/<package>.json
```

View reason for modification (if modified):

```bash
jq .modification_reason metadata/<package>.json
```

List all modified packages:

```bash
for f in metadata/*.json; do
  status=$(jq -r .modification_status "$f" 2>/dev/null)
  if [ "$status" = "modified" ]; then
    pkg=$(basename "$f" .json)
    reason=$(jq -r .modification_reason "$f" 2>/dev/null)
    echo "$pkg: $reason"
  fi
done
```

## Viewing Package Differences

To see what changes exist in a modified package compared to upstream Fedora:

```bash
# Show full diff for a package
./ci/dist_git.py diff bash

# Show summary statistics
./ci/dist_git.py diff bash --stat

# Show only which files changed
./ci/dist_git.py diff bash --name-only

# Show raw diff (includes Release: bumps and whitespace)
./ci/dist_git.py diff bash --raw

# Diff all modified packages
./ci/dist_git.py diff --all
```

**What's shown:**
- By default, the diff ignores Release: number changes (no-change rebuilds)
- Trailing whitespace and blank line changes are ignored
- Use `--raw` to see absolutely everything, including Release: bumps

**Package types:**
- **Modified packages**: Shows the differences
- **Clean packages**: Shows nothing (useful for verification)
- **Native packages**: Skips with message "no upstream to diff against"

## Marking Packages

### Mark as Modified

Use this when you make local changes to a package (backports, custom patches, etc.):

```bash
./ci/dist_git.py mark-modified <package> --modified \
  --reason "Brief explanation of why"
```

Examples:

```bash
# After backporting a patch
./ci/dist_git.py mark-modified gcc --modified \
  --reason "Backport CVE-2024-12345 fix from upstream"

# After custom spec change
./ci/dist_git.py mark-modified systemd --modified \
  --reason "Add custom service unit for Hummingbird"
```

The reason field is **required** and should be concise but descriptive. It helps
future maintainers understand why the package can't be auto-updated.

### Mark as Clean

Use this to re-enable automatic updates after confirming your changes are no
longer needed (e.g., the fix landed in Fedora):

```bash
./ci/dist_git.py mark-modified <package> --clean
```

This removes the `modified` status and allows the package to receive automatic
updates from Fedora again.

### Enable/Disable Upstream Version Tracking

Use this to opt a package into automatic upstream version checking via
`check_upstream_versions.py`:

```bash
# Enable upstream version tracking
./ci/dist_git.py mark-track-upstream <package> --enable

# Disable upstream version tracking
./ci/dist_git.py mark-track-upstream <package> --disable
```

When enabled, `"track_upstream": true` is set in the metadata. When disabled,
the field is removed. Only packages with this field set to `true` are checked
by `check_upstream_versions.py check` when no explicit package arguments are
given. To see all packages regardless of tracking status, use
`check_upstream_versions.py list`.

## How Auto-Updates Work

The `./ci/dist_git.py update` command (used by automation) checks modification
status before updating packages:

- **clean packages**: Updated automatically when new Fedora versions are available
- **modified packages**: Update blocked with error message showing the reason
- **native packages**: Update blocked (not sourced from Fedora)

To force-update a modified package (discarding local changes):

```bash
./ci/dist_git.py sync <package>
```

The `sync` command bypasses the modification check and force-updates to the
latest upstream version. After syncing, the package is automatically marked
clean.

## Resolving Merge Conflicts

When modified packages are updated from Fedora, `dist_git.py update` attempts to automatically merge local changes with the new upstream version using git's three-way merge. When conflicts occur, the update still succeeds but creates a commit with conflict markers, and the automation files a draft merge request labeled with `CONFLICT:` for manual resolution.

### Understanding Conflict Markers

Git uses this conflict marker structure:

```
<<<<<<< HEAD
Fedora's version (new upstream)
=======
Hummingbird's local modifications
>>>>>>> hummingbird-local
```

**ALL THREE markers must be removed** for a clean resolution.

### Update branch/MR structure

MRs are created on branches following the pattern:
```
chore/dist-git-update-PACKAGENAME
```

These branches are automatically created by the `dist_git_update` GitLab schedule.
If they have conflicts, they result in draft MRs with:
- Title prefix: `CONFLICT: chore(rpms): Update ...`
- Description listing the conflicting files
- `no-test` label to skip CI tests (saves resources since conflicts need manual resolution)

### Resolution Process

1. **Check out the conflict branch:**
   ```bash
   git fetch origin
   git checkout origin/chore/dist-git-update-PACKAGENAME
   ```

2. **Examine the conflict:**
   ```bash
   # Find all files with conflict markers
   git grep "^<<<<<<< HEAD" rpms/PACKAGENAME/

   # View the specific conflict
   git show HEAD:rpms/PACKAGENAME/PACKAGENAME.spec | grep -B5 -A10 "^<<<<<<< HEAD"
   ```

3. **Understand the local changes:**
   ```bash
   # Review commit history to understand why changes were made
   git log --oneline -- rpms/PACKAGENAME/
   git log -p -- rpms/PACKAGENAME/  # With diffs

   # Check the modification reason
   jq -r .modification_reason metadata/PACKAGENAME.json
   ```

   Understand the context for correct resolution:
   - What was the original purpose of the local change? Is it transient or permanent?
   - Is it a workaround for a bug, a security patch, or a configuration difference?
   - Does it affect other packages (e.g., nss builds nspr as a subpackage)?
   - Check spec file comments (e.g., NOTE: comments) for packaging details

   Decide which version to accept:
   - **Accept HEAD (Fedora)** for: release number lags, fixed workarounds that Fedora improved or addressed differently
   - **Keep hummingbird-local** for: security patches not in Fedora, FIPS requirements, critical fixes, and other permanent modifications
   - **Merge both** for: test skip lists, independent changes that don't conflict logically
   - **When in doubt:** Accept Fedora's version for packaging metadata (Release:, subpackage versions),
     keep Hummingbird's version for functional changes (patches, dependencies, build options)

4. **Resolve the conflict:** Edit the file to choose the appropriate version
   (HEAD, hummingbird-local, or merge both). Verify no markers remain:
     ```bash
     git grep -E "^(<<<<<<<|=======|>>>>>>>)" rpms/PACKAGENAME/
     ```

5. **Validate the resolution:** Check that local modifications are preserved:
   ```bash
   # Check the diff against upstream (works on working tree, staging not required)
   ./ci/dist_git.py diff PACKAGENAME

   # Compare with previous modification commits to verify
   git log -p -- rpms/PACKAGENAME/
   ```

   The diff should show only the intended local modifications (ignoring Release: bumps).
   This confirms the merge preserved your changes correctly. Note: `dist_git.py diff`
   compares the filesystem working tree against upstream, so it works before or after
   staging.

6. **Amend the commit:**
   ```bash
   git add rpms/PACKAGENAME/
   git commit --amend --no-edit
   ```

7. **Push the resolution:**
   ```bash
   git push origin HEAD:chore/dist-git-update-PACKAGENAME --force-with-lease --push-option merge_request.unlabel=no-test
   ```

   This removes the `no-test` label from the MR, which triggers CI tests to run and
   verifies the resolution works correctly. Some developers might have `origin` as
   read-only remote, and a different writable remote (e.g. `originw`).

### Common Conflicts

#### nss: Subpackage Release Numbers

The `nss` package builds `nspr` as a subpackage with its own release number offset.

**BACKGROUND:**
- `nss` builds both `nss` and `nspr` RPMs from the same source
- `nspr_release` uses an offset (`%[%baserelease+n]`) to avoid NVR clashes
- The spec file NOTE explains: reset to 1 when `nspr_version` changes, increment when only `nss` changes
- Fedora manages these offsets in their ecosystem to prevent conflicts

**CONFLICT EXAMPLE:**
```
<<<<<<< HEAD
%global nspr_release %[%baserelease+3]
=======
%global nspr_release %[%baserelease+1]
>>>>>>> hummingbird-local
```

**REASONING:**
When updating to a new upstream `nss` version from Fedora:
- Accept Fedora's `nspr_release` offset (HEAD) - they manage NVR clashes
- Our local offset was specific to Hummingbird rebuilds
- New upstream version should reset to Fedora's packaging values
- Don't try to "calculate" what it should be - trust Fedora's packaging

**RESOLUTION:** Accept HEAD (Fedora's value)


## Special Case: Rebuild-Only Changes

Release-only changes (no-change rebuilds) are automatically ignored by the
modification detection logic. This means:

- Bumping `Release: 3%{?dist}` → `Release: 3.1%{?dist}` does **not** mark the
  package as modified
- The package can still receive automatic Fedora updates
- The Release bump will be preserved if the update doesn't change the upstream
  Release field

You **do not need** to mark packages as modified for rebuild-only changes,
unless you want to explicitly prevent automatic updates for other reasons.

## CI Validation

The CI pipeline validates modification status consistency using
`make check`, which runs:

```bash
./ci/validate_package_modifications.py --all
```

This validation ensures:

1. All packages have a `modification_status` field
2. The value is one of: `clean`, `modified`, `native`
3. If `track_upstream` is present, it must be a boolean
4. Modified packages have a `modification_reason`
5. Native packages do not have source/branch/sha fields (Hummingbird-native only)
6. Git commit history matches the declared modification status

The validation runs on every merge request and push to main, failing the build
if metadata is inconsistent.

For local development, run the full validation:

```bash
./ci/validate_package_modifications.py --all
```

Or validate specific packages:

```bash
./ci/validate_package_modifications.py bash glibc gcc
```

### Validation Modes

The validation script has two modes:

**Fast mode (default)**: Checks git commit history patterns
```bash
./ci/validate_package_modifications.py --all
```
This validates that all commits since the last Sync follow standard patterns
(have Upstream: trailers). Runs in less than a minute for all packages.

**Thorough mode**: Clones upstream repos and compares filesystems
```bash
./ci/validate_package_modifications.py --all --thorough
```
This performs full filesystem comparisons with upstream Fedora repositories.
Slow and unreliable (hundreds of upstream dist-git clones) but authoritative -
validates actual state regardless of git commit history.

For CI and daily development, fast mode is sufficient. Use thorough mode when:
- Debugging discrepancies between metadata and actual state
- Auditing the entire repository for hidden modifications
- Investigating why a package can't be updated

## Workflow Examples

### Backporting a Patch

1. Add patch file and modify spec (see [Rebuilding Packages](../rebuilding-packages))
2. Commit the changes
3. **Mark as modified:**
   ```bash
   ./ci/dist_git.py mark-modified dnf5 --modified \
     --reason "Backport reproducible build fix (upstream PR#2522)"
   ```
4. Package is now protected from automatic Fedora updates

### Re-enabling Auto-Updates

When your backported fix lands in Fedora:

1. Verify the fix is in the latest Fedora version:
   ```bash
   ./ci/dist_git.py update dnf5  # This will fail with "modified" error
   ```
2. Mark the package clean:
   ```bash
   ./ci/dist_git.py mark-modified dnf5 --clean
   ```
3. Update from Fedora:
   ```bash
   ./ci/dist_git.py update dnf5  # Now succeeds
   ```

### Importing New Packages

When importing packages, modification status is set automatically:

```bash
# Fedora package → marked as "clean"
./ci/dist_git.py import fedora/neofetch

# Hummingbird-native package → marked as "native"
./ci/dist_git.py import hummingbird/custom-tool
```

No manual marking needed for imports.

## Troubleshooting

### CI Fails: "Missing modification_status field"

This means a metadata file is missing the required field. This means that the
package was not imported properly.

### CI Fails: "Marked as clean but package has modifications"

The package has local changes but metadata says it's clean. To fix:

1. Check what changed:
   ```bash
   git log -p -- rpms/<package>/
   ```
2. Mark as modified with the appropriate reason:
   ```bash
   ./ci/dist_git.py mark-modified <package> --modified --reason "..."
   ```

### CI Fails: "Marked as modified but package is actually clean"

The package has no local changes but is marked modified. To fix:

1. Verify it's actually clean:
   ```bash
   ./ci/dist_git.py update <package>  # Check if upstream matches
   ```
2. If confirmed clean, remove the modified status:
   ```bash
   ./ci/dist_git.py mark-modified <package> --clean
   ```

### Update Blocked: "Cannot auto-update <package>"

This is expected for modified packages. Options:

1. **Wait for fix to land in Fedora**, then mark clean and update
2. **Force-sync** to discard local changes:
   ```bash
   ./ci/dist_git.py sync <package>
   ```
3. **Keep blocked** if the local changes are still needed

## Related Documentation

- [Rebuilding Packages](../rebuilding-packages) - How to rebuild and backport patches
- [Updating Dist-git Packages](../updating-dist-git-packages) - How automatic updates work
