# dotnet8.0

The dotnet8.0 package

This is the .NET 8.0 package for Fedora.

This package is maintained by the Fedora DotNet SIG (Special Interest
Group). You can find out more about the DotNet SIG at:

- https://fedoraproject.org/wiki/SIGs/DotNet
- https://fedoraproject.org/wiki/DotNet
- https://lists.fedoraproject.org/archives/list/dotnet-sig@lists.fedoraproject.org/

Please report any issues [using
bugzilla](https://bugzilla.redhat.com/enter_bug.cgi?product=Fedora&component=dotnet8.0).

# Specification

This package follows [package naming and contents suggested by
upstream](https://docs.microsoft.com/en-us/dotnet/core/build/distribution-packaging),
with one exception. It installs dotnet to `/usr/lib64/dotnet` (aka
`%{_libdir}`).

# Contributing

The steps below are for the final package. Please only contribute to this
pre-release version this if you know what you are doing. Original instructions
follow.

## General Changes

1. Fork the repo.

2. Checkout the forked repository.

    - `git clone ssh://$USER@pkgs.fedoraproject.org/forks/$USER/rpms/dotnet8.0.git`
    - `cd dotnet8.0`

3. Make your changes. Don't forget to add a changelog.

4. Do local builds.

    - `fedpkg local`

5. Fix any errors that come up and rebuild until it works locally.

6. Do builds in koji.

    - `fedpkg scratch-build --srpm`

8. Commit the changes to the git repo.

    - `git add` any new patches
    - `git remove` any now-unnecessary patches
    - `git commit -a`
    - `git push`

9. Create a pull request with your changes.

10. Once the tests in the pull-request pass, and reviewers are happy, do a real
    build.

    - `fedpkg build`

11. For non-rawhide releases, file updates using bodhi to ship the just-built
    package out to users.

    - https://bodhi.fedoraproject.org/updates/new

    OR

    - `fedpkg update`

## Updating to an new upstream release

1. Fork the repo.

2. Checkout the forked repository.

    - `git clone ssh://$USER@pkgs.fedoraproject.org/forks/$USER/rpms/dotnet8.0.git`
    - `cd dotnet8.0`

3. Build the new upstream source tarball. Update the versions in the
   spec file. Add a changelog. This is generally automated by the
   following.

    - `./update-release <sdk-version> <runtime-version>`

    If this fails because of compiler errors, you might have to figure
    out a fix, then add the patch in `build-dotnet-tarball` script
    rather than the spec file.

4. Do local builds.

    - `fedpkg local`

5. Fix any errors that come up and rebuild until it works locally. Any
   patches that are needed at this point should be added to the spec file.

6. Do builds in koji.

    - `fedpkg scratch-build --srpm`

7. Upload the source archive to the Fedora look-aside cache.

    - `fedpkg new-sources path-to-generated-dotnet-source-tarball.tar.gz`

8. Commit the changes to the git repo.

    - `git add` any new patches
    - `git remove` any now-unnecessary patches
    - `git commit -a`
    - `git push`

9. Create a pull request with your changes.

10. Once the tests in the pull-request pass, and reviewers are happy, do a real
    build.

    - `fedpkg build`

11. For non-rawhide releases, file updates using bodhi to ship the just-built
    package out to users.

    - https://bodhi.fedoraproject.org/updates/new

    OR

    - `fedpkg update`

# Testing

This package uses CI tests as defined in `tests/test.yml`. Creating a
pull-request or running a build will fire off tests and flag any issues. We have
enabled gating (via `gating.yaml`) on the tests. That prevents a build
that fails any test from being released until the failures are waived.

The tests themselves are contained in this external repository:
https://github.com/redhat-developer/dotnet-regular-tests/
