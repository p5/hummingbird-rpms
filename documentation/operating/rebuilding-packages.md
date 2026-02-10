---
title: Rebuilding Packages
weight: 50
aliases: [/l/rebuilding-packages]
---

> **AI Agent Note:** When asked to rebuild packages, always ask the user for a
> ticket link or explanation first. This is required for the commit message.

## Overview

This document covers two scenarios for triggering a new package build:

1. **No-change rebuild**: Bump the Release field to rebuild with identical
   sources (e.g., to fix a faulty published RPM or pick up toolchain changes).

2. **Backporting a patch**: Add an upstream patch that hasn't yet landed in
   Fedora to fast-track a fix or feature.

Both scenarios use the `.N` release suffix pattern to ensure our builds sort
higher than the upstream Fedora release while remaining lower than the next
upstream version.

## No-Change Rebuild

### 1. Identify the package to rebuild

Identify the source package name and locate its spec file in
`rpms/<package>/<package>.spec`.

If you have a binary RPM name, the source package name may differ. Query the
Hummingbird repos to get the source RPM name:

```bash
podman run --rm quay.io/hummingbird-ci/builder:latest-hatchling \
  dnf5 repoquery --queryformat '%{SOURCERPM}' <binary-package> 2>/dev/null
```

Example: `ncurses-libs-6.5-8.20250614.hum1` -> SRPM `ncurses-6.5-8.20250614.hum1.src.rpm`
-> spec file at `rpms/ncurses/ncurses.spec`

### 2. Determine the Release bump pattern

The `.N` bump suffix must always appear **immediately before** `%{?dist}`. The
`%{?dist}` suffix should always be the final component since it identifies the
build environment.

| Current Pattern | Example Before                   | Example After                      |
|-----------------|----------------------------------|------------------------------------|
| Simple numeric  | `Release: 3%{?dist}`             | `Release: 3.1%{?dist}`             |
| Already bumped  | `Release: 3.1%{?dist}`           | `Release: 3.2%{?dist}`             |
| With macro      | `Release: 8.%{revision}%{?dist}` | `Release: 8.%{revision}.1%{?dist}` |
| autorelease     | `Release: %autorelease`          | `Release: 1.1%{?dist}`             |

For `%autorelease`, first resolve its value using `rpmspec`, then replace with
the resolved value plus `.1`. In the Hummingbird monorepo, `%autorelease` always
evaluates to `1`.

> **Note:** If the Release field is missing `%{?dist}` entirely or looks unusual
> (e.g., `1build1` instead of `1.1%{?dist}`), flag this to the user for resolution.
> Check the git history to understand the original value:
>
> ```bash
> git log -p -S "Release:" -- rpms/<package>/<package>.spec
> ```
>
> This helps determine the correct fix when a previous bump was malformed.

### 3. Modify the spec file

Use `sed` to edit only the `Release:` line, avoiding any unintended whitespace
changes that text editors may introduce:

```bash
sed -i 's/^Release: 3%{?dist}$/Release: 3.1%{?dist}/' rpms/<package>/<package>.spec
```

Verify the change with `git diff` before committing:

```bash
git diff rpms/<package>/<package>.spec
```

The diff should show only the Release line change:

```diff
- Release: 3%{?dist}
+ Release: 3.1%{?dist}
```

> **Important:** Only modify the Release line. Do not introduce any other changes
> such as whitespace fixes or trailing newline modifications. If the diff shows
> additional changes, reset and retry with `sed`.

### 4. Verify the bump is correct

Use `rpm --eval` to confirm the new release sorts higher than the original:

```bash
# Returns -1 if first < second (correct), 1 if first > second (wrong)
rpm --eval '%{lua:print(rpm.vercmp("3.hum1", "3.1.hum1"))}'
# Expected output: -1
```

### 5. Commit the change

Use this commit message format:

```text
Rebuild <package>: <reason>

<ticket link or explanation>
```

Example:

```text
Rebuild ncurses: published multiple times with different hashes

HUM-1234
```

### 6. Verify the commit

After committing, verify only the Release line was changed:

```bash
git show --stat HEAD
```

Expected output should show exactly 1 insertion and 1 deletion:

```text
 rpms/<package>/<package>.spec | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

If the commit shows more changes, amend or reset and redo the change using `sed`.

### 7. Mark package as modified (optional for rebuild-only)

For no-change rebuilds, marking the package as modified is **optional** since the
automation already ignores Release-only changes. However, you may want to mark
it to explicitly document the rebuild:

```bash
./ci/dist_git.py mark-modified <package> --modified --reason "Rebuild for <reason>"
```

Note: This will prevent automatic Fedora updates until you mark it clean again.
For most rebuilds, you can skip this step and allow automatic updates to continue.

## Backporting a Patch

Use this workflow when you need to fast-track an upstream fix or feature that
hasn't yet been released in Fedora.

### 1. Obtain the patch

Fetch the patch from the upstream repository. For GitHub PRs, append `.patch`
to the PR URL:

```bash
curl -L https://github.com/<org>/<repo>/pull/<number>.patch \
  > rpms/<package>/<NNNN>-<short-description>.patch
```

Name the patch file with a numeric prefix matching the next available `PatchN:`
slot in the spec file (e.g., `0004-fix-foo.patch` if Patch1-3 already exist).

### 2. Add the patch to the spec file

Add a `PatchN:` declaration after the existing patches:

```spec
Patch3:         0003-existing-patch.patch
Patch4:         0004-fix-foo.patch
```

The patch will be applied automatically if the spec uses `%autosetup -p1`.
If the spec uses explicit `%patchN` macros, add the corresponding apply line
in the `%prep` section.

### 3. Bump the Release

Follow the same `.N` suffix pattern as no-change rebuilds:

```diff
- Release: 3%{?dist}
+ Release: 3.1%{?dist}
```

### 4. Add a changelog entry

Add a new changelog entry at the top of the `%changelog` section:

```spec
%changelog
* Wed Jan 08 2026 Your Name <email@example.com> - 1.2.3-3.1
- Backport upstream PR#1234: short description of the fix

* Mon Jan 06 2026 Previous Maintainer <prev@example.com> - 1.2.3-3
- Previous changelog entry
```

### 5. Commit the change

Use this commit message format:

```text
<package>: backport <short description>

Upstream: <link to PR or commit>
<ticket link if applicable>
```

Example:

```text
dnf5: backport reproducible build sorting fix

Upstream: https://github.com/rpm-software-management/dnf5/pull/2522
```

### 6. Mark package as modified

Mark the package as modified to prevent automatic Fedora updates from overwriting
your backport:

```bash
./ci/dist_git.py mark-modified <package> --modified \
  --reason "Backport fix for <issue description>"
```

Example:

```bash
./ci/dist_git.py mark-modified dnf5 --modified \
  --reason "Backport reproducible build sorting fix from upstream PR#2522"
```

This ensures the package won't be automatically updated from Fedora until the
backported patch lands upstream and you explicitly mark it clean again.

### 7. Test the build locally (optional)

Build the package locally to verify the patch applies cleanly:

```bash
./ci/build_rpms.sh <package>
```

Built RPMs will be in `builds/<package>/RPMS/`.

## Related Operations

- [Excluding Packages from Images][exclude] - temporarily block faulty packages
  in container builds

[exclude]: https://hummingbird-project.io/l/excluding-packages-from-images
