# Contributing to Hummingbird RPMs

Thank you for your interest in contributing! This repository contains RPM packaging, minimal tests, and CI plumbing used by Hummingbird to build, lint, and validate RPMs in containers and Testing Farm.

This guide is adapted from the Hummingbird containers contribution guide and aligned with our workflows and tooling. See the original for broader context: [Hummingbird Containers CONTRIBUTING](https://gitlab.com/redhat/hummingbird/containers/-/blob/main/CONTRIBUTING.md).

## Code of Conduct
Be respectful and constructive. By participating, you agree to uphold a professional and inclusive environment.

## Repository layout
- `rpms/<package>/` – RPM dist-gits (spec, sources)
- `ci/` – helper scripts and default tests
  - `build_rpms.sh` – build RPMs using Mock in the Konflux-compatible container
  - `run_tests_rpm.sh` – run rpmlint and install/rebuild tests in a container
  - `default-tests/tests-rpm.yml` – default tests included for all packages
  - `run_tests_rpm.fmf` – tmt/Testing Farm entry point
- `konflux-templates/` – Konflux/PAC resources
- `mock/` – mock configuration
- `test/rpms/<package>.yml` – package-specific tests

## Prerequisites
- Fedora or RHEL-like environment
- Podman
- rpmlint
- tmt (optional, for local TF-style runs)
- jq, python3, python3-yaml (used by `run_tests_rpm.sh`)

## Build locally
Build a package’s SRPM and RPMs using the Konflux-aligned environment:

```bash
./ci/build_rpms.sh <package_name>
# Results are written to: /tmp/konflux-build-<package_name>-*/results/
```

## Test locally (containerized)
Run the default and package-specific tests against one or more built RPMs:

```bash
# Basic usage (binary rpm)
./ci/run_tests_rpm.sh --rpm /path/to/pkg-1.2-1.fcXX.x86_64.rpm <package_name>

# Include source RPM tests
./ci/run_tests_rpm.sh \
  --rpm /path/to/pkg-1.2-1.fcXX.x86_64.rpm \
  --src-rpm /path/to/pkg-1.2-1.fcXX.src.rpm \
  <package_name>

# Test all RPMs in the build output directory after build_rpms.sh
./ci/run_tests_rpm.sh $(printf -- '--rpm %s ' builds/<package_name>/RPMS/*.rpm) \
  --repo-dir builds/<package_name>/RPMS/ \
  --src-rpm builds/<package_name>/SRPMS/*.src.rpm \
  <package_name>
```

Notes:
- Tests run inside a Podman container.
- The test image defaults to `quay.io/hummingbird/core-runtime:latest-builder`. You can override via `TEST_IMAGE`:

```bash
TEST_IMAGE=quay.io/hummingbird/core-runtime:specific-tag ./ci/run_tests_rpm.sh --rpm /path/to/pkg.rpm <package_name>
```

- Container execution is performed as root with `HOME=/root` to avoid XDG state permission issues in dnf5.

## Test in tmt/Testing Farm locally
You can drive the same FMF test locally with tmt. The FMF test expects an OCI artifact that contains RPMs, referenced via `IMAGE_URL` (Testing Farm sets this automatically). For local trials you can point to any compatible OCI artifact or skip the ORAS pull logic and directly call the script.

```bash
# If using an OCI artifact with RPMs
IMAGE_URL="oci://registry/namespace/artifact:tag_or_digest" tmt run -a

# Or run the script directly with built RPMs (bypassing the FMF wrapper)
./ci/run_tests_rpm.sh --rpm /path/to/pkg.rpm --src-rpm /path/to/pkg.src.rpm <package_name>
```

If you need longer time in Testing Farm, the FMF test includes `duration`, which you can adjust in `ci/run_tests_rpm.fmf`.

## Branching and pull requests
- Create feature branches from the default branch.
- Keep edits focused and small; separate unrelated changes into separate PRs.
- Include meaningful commit messages (why + what). Reference related issues if applicable.
- PRs must pass CI (build + tests). Fix lint/test failures or mark known failures properly.

## Commit message conventions
- First line: short imperative summary (≤ 72 chars)
- Body (optional): context, rationale, and user/ops impact
- Reference issues using standard notation (e.g. "Fixes: #123")

## Packaging and testing guidelines
- Spec files should be reproducible and minimal.
- Prefer pinned container digests for CI images where feasible. If a tag and digest are both present (`name:tag@sha256:<digest>`), the digest is authoritative for content selection.
- Default tests in `ci/default-tests/tests-rpm.yml` must be fast, deterministic, and safe for all packages.
- Package-specific tests (`rpms/<package>/tests-rpm.yml`) can override or extend defaults. Keep them bounded in runtime and dependencies.
- When possible, capture flaky or environmental issues under `known_issues` in test YAML with clear matching patterns and descriptions.

## Style
- Shell: bash with `set -euo pipefail`, readable variable names, and early returns where reasonable.
- YAML: consistent indentation and quoting; prefer explicitness over magic.
- Comments: add when necessary to explain non-obvious rationale; avoid restating the code.

## Security and supply chain
- Avoid embedding credentials or secrets; use environment variables or CI secret stores.
- Prefer pulling images by digest for stability and repeatability in CI.
- Validate inputs and sanitize any paths used by scripts.

## Reporting issues
Open an issue describing the problem, reproduction steps, and environment. Attach logs (build/test) when possible. If the failure is intermittent, call that out explicitly.

## Licensing
Ensure files include appropriate licenses and that any third-party content is compatible with the project's license.

## Thank you
Your contributions make the Hummingbird RPMs better for everyone. We appreciate your time and feedback!
