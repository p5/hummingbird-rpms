# Contributing to Hummingbird RPMs

Thank you for your interest in contributing! This repository contains RPM packaging, minimal tests, and CI plumbing used by Hummingbird to build, lint, and validate RPMs in containers and Testing Farm.

## Getting Started

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/p5/hummingbird-rpms.git
cd hummingbird-rpms

# Prerequisites (Fedora or RHEL-like environment)
sudo dnf install -y podman rpmlint jq python3 python3-yaml

# Optional: install tmt for local Testing Farm-style runs
sudo dnf install -y tmt
```

### Repository Structure

- `rpms/<package>/` – RPM dist-gits (spec files, sources)
- `ci/` – build/test scripts and configuration
- `metadata/<package>.json` – package metadata and tracking
- `.tekton/` – Konflux pipeline definitions

## Building RPMs Locally

### Basic Build

Build RPMs using Mock in a Konflux-compatible container:

```bash
./ci/build_rpms.sh <package_name>
# Results: /tmp/konflux-build-<package_name>-*/results/
```

For debugging build issues:

```bash
# Interactive shell before build
./ci/build_rpms.sh --shell-before <package_name>

# Interactive shell after build
./ci/build_rpms.sh --shell-after <package_name>
```

**macOS users (Lima VM):** Use `--build-dir` to specify a VM-native path:

```bash
limactl shell fedora bash -c 'cd /path/to/repo && ./ci/build_rpms.sh --build-dir /tmp/rpm-build <package_name>'
```

### Testing

Run tests locally in a container:

```bash
# After building, test the RPMs
./ci/run_tests_rpm.sh --rpm /path/to/pkg.rpm --src-rpm /path/to/pkg.src.rpm <package_name>
```

## Submitting Changes

### Branch Naming Convention

**All feature branches must use the `factory/` prefix:**

```bash
# Create a feature branch
git checkout -b factory/fix-bash-issue
git checkout -b factory/add-new-package

# Push your branch
git push origin factory/your-branch-name
```

Automated tooling and CI workflows expect this naming convention.

### Pull Request Process

1. **Create a focused branch** from `main` using the `factory/` prefix
2. **Make your changes** and commit with clear messages:
   ```bash
   git add -A
   git commit -m "Fix: description of what and why"
   ```
3. **Push to GitHub:**
   ```bash
   git push origin factory/your-branch-name
   ```
4. **Open a pull request** targeting the `main` branch
5. **Ensure CI passes** – all builds and tests must succeed
6. **Address review feedback** promptly

### Code Review Expectations

- **Responsiveness:** Respond to review comments within 2-3 business days
- **CI is required:** All checks must pass before merge
- **Focus and scope:** Keep PRs small and focused on a single change
- **Commit messages:** Use imperative mood ("Fix bug" not "Fixed bug"), reference issues when applicable
- **Tests:** Add tests for new functionality; ensure existing tests pass
- **Documentation:** Update relevant docs if behavior changes

Reviewers will check for:
- Code correctness and adherence to project conventions
- Security implications (no hardcoded secrets, input validation)
- Reproducibility and minimal dependencies in spec files
- Clear rationale for changes

## Code Style

- **Shell:** Use `set -euo pipefail`, clear variable names
- **YAML:** Consistent indentation, explicit over implicit
- **Python:** Follow project conventions (see existing code in `ci/`)
- **Commit messages:** Short summary (≤72 chars), optional detailed body

## Common Operations

### Package Management

Import packages from Fedora/CentOS dist-git using `ci/dist_git.py`:

```bash
# Import a new package (defaults to rawhide)
./ci/dist_git.py import fedora/bash

# Update all packages or a specific one
./ci/dist_git.py update
./ci/dist_git.py update bash

# Sync package to upstream (discard local modifications)
./ci/dist_git.py sync bash
```

See the [operating documentation](documentation/operating/) for detailed guides on:
- [Adding native packages](documentation/operating/adding-native-packages.md)
- [Rebuilding packages](documentation/operating/rebuilding-packages.md)
- [Package modification tracking](documentation/operating/package-modification-tracking.md)
- [Updating dist-git packages](documentation/operating/updating-dist-git-packages.md)

### Build Configuration

Customize per-package settings in `ci/package-overrides.yaml`:

```yaml
package_name:
  timeout_hours: 12
  build_platforms:
    - "linux-d160-c8xlarge/arm64"
    - "linux-d160-c8xlarge/amd64"
```

After changes, regenerate pipelines: `make generate`

## Additional Resources

- [Hummingbird Containers Guide](https://gitlab.com/redhat/hummingbird/containers/-/blob/main/CONTRIBUTING.md) – broader project context
- [Konflux Documentation](https://konflux.pages.redhat.com/docs/) – CI/CD platform details
- [Operating Documentation](documentation/operating/) – detailed operational guides

## Reporting Issues

Open an issue with:
- Problem description and reproduction steps
- Environment details (OS, tool versions)
- Relevant logs or error messages
- Whether the issue is intermittent

## Code of Conduct

Be respectful and constructive. Maintain a professional and inclusive environment.

---

Thank you for contributing to Hummingbird RPMs!
