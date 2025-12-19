---
title: Rebuilding Packages
weight: 50
aliases: [/l/rebuilding-packages]
---

> **AI Agent Note:** When asked to rebuild packages, always ask the user for a
> ticket link or explanation first. This is required for the commit message.

## Overview

A no-change rebuild bumps the Release: field to trigger a new build without
modifying the package sources, using the `.N` numeric suffix pattern described
below.

## Workflow

### 1. Identify the package to rebuild

Identify the source package name and locate its spec file in
`rpms/<package>/<package>.spec`.

If you have a binary RPM name, the source package name may differ. Query the
Hummingbird repos to get the source RPM name:

```bash
podman run --rm quay.io/hummingbird-ci/builder:latest-hatchling \
  dnf5 repoquery --queryformat '%{SOURCERPM}' <binary-package> 2>/dev/null
```

Example: `ncurses-libs-6.5-8.20250614.hum1` → SRPM `ncurses-6.5-8.20250614.hum1.src.rpm`
→ spec file at `rpms/ncurses/ncurses.spec`

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

## Related Operations

- [Excluding Packages from Images][exclude] - temporarily block faulty packages
  in container builds

[exclude]: https://hummingbird-project.io/l/excluding-packages-from-images
