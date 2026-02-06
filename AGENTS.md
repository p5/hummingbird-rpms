# RPMs Repository Guidelines

## Operations Index

Common operational tasks that users or AI agents may need to perform:

| Operation                   | Documentation                                                                      | When to use                                              |
|-----------------------------|------------------------------------------------------------------------------------|----------------------------------------------------------|
| Rebuild package (no-change) | [Rebuilding Packages](documentation/operating/rebuilding-packages.md)              | Faulty RPM published; need to bump Release for rebuild   |
| Backport a patch            | [Rebuilding Packages](documentation/operating/rebuilding-packages.md)              | Fast-track an upstream fix not yet in Fedora             |
| Update dist-git packages    | [Updating Dist-git Packages](documentation/operating/updating-dist-git-packages.md) | Test or trigger automated package updates from Fedora    |
| Konflux resource deployment | [Konflux Resource Deployment](documentation/background/konflux-resource-deployment.md) | Understand how Konflux resources are deployed          |
