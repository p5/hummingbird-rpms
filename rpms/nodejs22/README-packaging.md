# Packaging Node.js
These instructions are applicable as of 2023-04-27, following the
implementation of https://www.fedoraproject.org/wiki/Changes/NodejsRepackaging

These instructions use Node.js 20 as an example, but should be applicable to
any major version. Exceptions will be identified as needed.


## Basic steps to update to a new release

1.  Run the following command to automatically update the specfile and SOURCES:

    ```
    ./nodejs-sources 20.1.0
    ```

    This will download the tarball from nodejs.org, strip out the bundled
    OpenSSL code, extract the versions of the bundled sources, pull down the
    ICU data files and update the spec file with this new information, also
    pushing the rebuilt tarball into the Fedora lookaside cache.

2.  Verify that the patches still apply by running `fedpkg prep`. If they do
    not, follow the steps under "Resolving Patch Conflicts".

3.  (Preferred) Perform a scratch-build on at least one architecture

    ```
    fedpkg scratch-build [--arch x86_64] --srpm
    ```

    Verify that it built successfully.

4.  Commit the code locally and push it to all active Fedora branches.

    ```
    git commit -sam "Update to version 20.1.0"
    ```

    ```
    git push origin rawhide rawhide:f38 rawhide:f37
    ```

5.  Build for all active Fedora branches

    ```
    for i in f37 f38 rawhide ; do fedpkg --release $i build --nowait ; done
    ```


## Basic steps to update the packaging

1.  Make all changes in the `packaging/nodejs.spec.j2` file.

2.  When finished, run

    ```
    ./nodejs-sources 20.1.0 --no-push
    ```

    which will regenerate the nodejs20.spec file with the appropriate values.
    The `--no-push` argument is used to avoid uploading a new tarball to the
    lookaside cache.[^1]

3. (Preferred) Perform a scratch-build on at least one architecture

    ```
    fedpkg scratch-build [--arch x86_64] --srpm
    ```

    Verify that it built successfully.

4.  Commit the code locally and push it to all active Fedora branches.

    ```
    git commit -sam "Update to version 20.1.0"
    ```

    ```
    git push origin rawhide rawhide:f38 rawhide:f37
    ```

5.  Build for all active Fedora branches

    ```
    for i in f37 f38 rawhide ; do fedpkg --release $i build --nowait ; done
    ```


## Resolving Patch Conflicts

1.  Clone the upstream Node.js repository

    ```
    git clone -o upstream git://github.com/nodejs/node.git nodejs-upstream
    ```

2. Rebase the Fedora patches atop the latest release

    ```
    pushd nodejs-upstream
    ```

    ```
    git checkout -b fedora-v20 v20.1.0
    ```

    ```
    git am -3 ../nodejs-fedora/*.patch
    ```

    If the patches do not apply cleanly, resolve the merges appropriately. Once
    they have all been applied, output them again:

    ```
    git format-patch -M --patience --full-index -o ../nodejs20 v20.1.0..HEAD
    ```

    ```
    popd
    ```

3.  Resume the basic process.


[^1]: Due to non-deterministic behavior, stripping out the OpenSSL bits from
    the upstream tarball and recompressing it will result in a different
    checksum hash. This isn't harmful, but wastes bandwidth and storage space,
    so use `--no-push` when possible.
