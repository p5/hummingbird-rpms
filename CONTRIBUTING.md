# Contributing to Hummingbird RPMs

Thank you for your interest in contributing to Project Hummingbird! This guide covers the essentials for getting started.

## Getting Started

### Clone and Setup

```bash
git clone https://github.com/p5/hummingbird-rpms.git
cd hummingbird-rpms
```

**Prerequisites:**
- Fedora or RHEL-like environment
- Podman installed
- Python 3 with pyyaml and jq

## Building RPMs Locally

Build a package using the Konflux-aligned mock environment:

```bash
./ci/build_rpms.sh <package_name>
```

Results are written to `/tmp/konflux-build-<package_name>-*/results/`

**macOS/Lima users:** Use `--build-dir` to specify a native VM filesystem path:

```bash
limactl shell fedora bash -c 'cd /path/to/repo && ./ci/build_rpms.sh --build-dir /tmp/rpm-build <package_name>'
```

### Testing Locally

Test built RPMs in a container:

```bash
./ci/run_tests_rpm.sh --rpm /path/to/pkg.rpm --src-rpm /path/to/pkg.src.rpm <package_name>
```

## Submitting Changes

### Branch Naming

- Create feature branches from `main`
- Use descriptive names: `fix/package-name-issue`, `add/new-package`, etc.
- For automated workflows, use `factory/` prefix for factory PRs

### Pull Request Process

1. **Create a branch** from main with your changes
2. **Keep changes focused** - one logical change per PR
3. **Write clear commit messages:**
   - First line: short imperative summary (≤72 chars)
   - Body: explain why, not just what
   - Reference issues: `Fixes: #123` or `Closes: #456`
4. **Ensure CI passes** - both build and tests must succeed
5. **Submit the PR** and wait for review

## Code Review Expectations

- **Response time:** Maintainers typically review within 1-2 business days
- **CI must pass:** PRs with failing tests won't be merged
- **Be responsive:** Address feedback promptly and clarify questions
- **Keep it professional:** Respectful, constructive communication

### What Reviewers Look For

- Code quality and correctness
- Test coverage for changes
- Adherence to existing patterns
- Clear documentation for non-obvious changes
- No hardcoded credentials or security issues

## Additional Resources

- [Operating guides](./documentation/operating/) - Package management workflows
- [Mock configuration](./mock/mock.cfg) - Build environment setup
- [Package overrides](./ci/package-overrides.yaml) - Custom build settings
- [Hummingbird Containers](https://gitlab.com/redhat/hummingbird/containers) - Parent project

## Getting Help

- **Issues:** Found a bug? [Open an issue](https://github.com/p5/hummingbird-rpms/issues/new)
- **Questions:** Reach out via issue comments or project channels

Thank you for contributing to Hummingbird!
