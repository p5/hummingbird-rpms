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
3. Modified packages have a `modification_reason`
4. Native packages do not have source/branch/sha fields (Hummingbird-native only)
5. Git commit history matches the declared modification status

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
