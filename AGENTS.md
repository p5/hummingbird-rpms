# RPMs Repository Guidelines

## Operations Index

Common operational tasks that users or AI agents may need to perform:

| Operation                   | Documentation                                                                      | When to use                                              |
|-----------------------------|------------------------------------------------------------------------------------|----------------------------------------------------------|
| Add native package          | [Adding Native Packages](documentation/operating/adding-native-packages.md)        | Add new package not imported from Fedora                 |
| Rebuild package (no-change) | [Rebuilding Packages](documentation/operating/rebuilding-packages.md)              | Faulty RPM published; need to bump Release for rebuild   |
| Backport a patch            | [Rebuilding Packages](documentation/operating/rebuilding-packages.md)              | Fast-track an upstream fix not yet in Fedora             |
| Mark package modified       | [Package Modification Tracking](documentation/operating/package-modification-tracking.md) | Track local changes; prevent automatic Fedora updates    |
| View package differences    | [Package Modification Tracking](documentation/operating/package-modification-tracking.md) | See what changed in modified packages vs Fedora          |
| Update dist-git packages    | [Updating Dist-git Packages](documentation/operating/updating-dist-git-packages.md) | Test or trigger automated package updates from Fedora    |
| Konflux resource deployment | [Konflux Resource Deployment](documentation/background/konflux-resource-deployment.md) | Understand how Konflux resources are deployed          |

## Development Guidelines

### Testing Requirements

When modifying `ci/dist_git.py`:
- **Add tests** for new commands or functionality in `test/test_dist_git.py`
- Run `make check` to verify all tests pass before committing
- Test coverage is tracked - aim to test all user-facing behavior
- Examples: See existing tests like `test_import`, `test_update`, `test_mark_modified_with_reason`

When modifying validation or CI scripts:
- Ensure `make check` passes (includes linting, type checking, and validation)
- Add tests if the change affects user-facing behavior
