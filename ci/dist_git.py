#!/usr/bin/env python3
"""
dist-git importer for Hummingbird rpms repository.

This tool imports and syncs Fedora/CentOS dist-git packages
into the local rpms/ directory while tracking metadata in per-package
import.json files.
"""

import argparse
import http.client
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import xmlrpc.client
import yaml
from pathlib import Path
from specfile import Specfile
from typing import TypedDict, cast

ROOT_DIR = Path(__file__).resolve().parent.parent
RPMS_DIR = ROOT_DIR / 'rpms'
METADATA_DIR = ROOT_DIR / 'metadata'
RELEASES_JSON = ROOT_DIR / 'upstream-releases.json'
PACKAGE_OVERRIDES_YAML = ROOT_DIR / 'ci' / 'package-overrides.yaml'
RENAMED_PACKAGES_JSON = ROOT_DIR / 'ci' / 'renamed_packages.json'

# Global imports dict, loaded at startup
imports: dict[str, 'PackageMetadata'] = {}

# Global releases dict, loaded at startup
releases: dict[str, dict[str, str]] = {}

# Global sign-off flag, set from command line
sign_off: bool = False


class PackageMetadata(TypedDict):
    """Metadata stored in metadata/<package>.json for each package."""
    source: str
    branch: str
    sha: str
    version: str
    release: str


class KojiBuild(TypedDict, total=False):
    """Koji build result from getBuild() API."""
    build_id: int
    nvr: str
    state: int
    source: str


def uses_autorelease(package_dir: Path) -> bool:
    """Check if the spec file in package_dir uses %autorelease."""
    spec_files = list(package_dir.glob('*.spec'))
    if len(spec_files) != 1:
        return False

    spec_content = spec_files[0].read_text()
    # Check for %autorelease in Release: line (possibly with options like -b, -e, etc.)
    return bool(re.search(r'^Release:\s*%\{?\??autorelease\b', spec_content, re.MULTILINE))


def parse_spec_version(package_dir: Path) -> tuple[str, str]:
    """Extract version and release from package directory's spec file."""
    # Find the spec file
    spec_files = list(package_dir.glob('*.spec'))
    if len(spec_files) != 1:
        sys.exit(f"ERROR: Expected exactly one .spec file in {package_dir}, found {spec_files}")

    spec_file = spec_files[0]

    # Use rpmspec to query the resolved version and release
    # Set dist to %{nil} to get release without dist suffix
    # Set _sourcedir so rpmspec can find source files referenced in the spec
    rpmspec = subprocess.run(
        ['rpmspec', '-q', '--qf', '%{VERSION}\n%{RELEASE}\n',
         '--define=dist %{nil}', f'--define=_sourcedir {package_dir}', '--srpm', str(spec_file)],
        stdout=subprocess.PIPE, text=True, check=True)
    lines = rpmspec.stdout.strip().splitlines()
    try:
        return lines[0], lines[1]
    except IndexError as e:
        raise ValueError(f"Unexpected rpmspec output for {spec_file}: {rpmspec.stdout}") from e


def rename_spec_validate(original_name: str, original_dir: Path) -> str:
    """Read the new package name from spec file and validate it has been changed.

    Returns the new package name from the spec file.
    Exits with error if the Name field has not been changed from the original.
    """

    spec_file = original_dir / f"{original_name}.spec"
    current_spec = Specfile(str(spec_file), sourcedir=original_dir)
    new_name = current_spec.name

    spec_file_git_path = f'rpms/{original_name}/{original_name}.spec'

    git_result = run_git('show', f'HEAD:{spec_file_git_path}', cwd=ROOT_DIR, check=False)
    if git_result.returncode != 0:
        sys.exit(f"ERROR: Could not retrieve original spec file from git: {spec_file_git_path}")

    # Use a temp directory so we can copy source files needed by %load directives
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_spec = Path(tmpdir) / f"{original_name}.spec"
        tmp_spec.write_text(git_result.stdout)

        # Copy all non-spec source files to temp dir (for %load macros.* etc.)
        for src_file in original_dir.iterdir():
            if src_file.is_file() and src_file.suffix != '.spec':
                shutil.copy(src_file, tmpdir)

        original_spec = Specfile(str(tmp_spec), sourcedir=Path(tmpdir))
        original_spec_name = original_spec.name

    if original_spec_name == new_name:
        sys.exit(f"ERROR: Name field in {spec_file.name} has not been changed (still '{new_name}')\n"
                 f"       Please edit the spec file and change the Name: field before running rename")
    return new_name


def load_package_metadata(package_name: str) -> PackageMetadata | None:
    """Load package metadata from metadata/<package>.json."""
    import_file = METADATA_DIR / f'{package_name}.json'
    if not import_file.exists():
        return None
    with open(import_file) as f:
        data = json.load(f)
        if not data:
            return None
        return cast(PackageMetadata, data)


def save_package_metadata(package_name: str, metadata: PackageMetadata) -> None:
    """Save package metadata to metadata/<package>.json."""
    import_file = METADATA_DIR / f'{package_name}.json'
    METADATA_DIR.mkdir(exist_ok=True)
    with open(import_file, 'w') as f:
        json.dump(metadata, f, indent=2, sort_keys=True)
        f.write('\n')  # Ensure trailing newline


def get_all_imported_packages() -> dict[str, PackageMetadata]:
    """Scan metadata/ directory and load all package metadata files."""
    all_imports: dict[str, PackageMetadata] = {}
    if not METADATA_DIR.exists():
        return all_imports

    for metadata_file in METADATA_DIR.glob('*.json'):
        package_name = metadata_file.stem
        metadata = load_package_metadata(package_name)
        if metadata:
            all_imports[package_name] = metadata

    return all_imports


def run_git(*args: str, cwd: Path | str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git command and return its stdout/exit code.

    For network operations (clone, fetch, pull), retries up to 3 times with exponential backoff
    to handle transient network failures.
    """
    # Network operations that should be retried on failure
    network_ops = {'clone', 'fetch', 'pull'}
    should_retry = len(args) > 0 and args[0] in network_ops

    max_retries = 3 if should_retry else 1
    retry_delay = 2  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            return subprocess.run(['git', *args], cwd=cwd, check=check, stdout=subprocess.PIPE, text=True)
        except subprocess.CalledProcessError as e:
            if attempt < max_retries - 1:
                logging.warning("Git %s failed (attempt %d/%d): %s", args[0], attempt + 1, max_retries, e)
                logging.info("Retrying in %d seconds...", retry_delay)
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                # Last attempt failed, re-raise the exception
                raise

    # This should never be reached since max_retries >= 1 and loop always returns or raises
    raise RuntimeError("Unexpected: git command loop completed without return or exception")


def run_git_commit(*args: str, cwd: Path | str | None = None) -> subprocess.CompletedProcess[str]:
    """Run git commit with optional --signoff flag."""
    commit_args = ['commit']
    if sign_off:
        commit_args.append('--signoff')
    commit_args.extend(args)
    return run_git(*commit_args, cwd=cwd)


def check_jinja2_available() -> None:
    """Check if jinja2 command-line tool is available."""
    try:
        subprocess.run(['jinja2', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        sys.exit("ERROR: jinja2 command-line tool is not available.\n"
                 "       Please install jinja2-cli (pip install jinja2-cli) or similar package.")


def expand_url_shortcut(url: str) -> str:
    """Expand URL shortcuts to full dist-git URLs."""
    if url.startswith('fedora/'):
        package = url.removeprefix('fedora/')
        return f'https://src.fedoraproject.org/rpms/{package}.git'
    return url


def update_releases() -> None:
    """Update upstream-releases.json"""

    releases: dict[str, dict[str, str]] = {}

    # Fedora: get them from Bodhi
    logging.info("Fetching Fedora releases from Bodhi API...")
    url = 'https://bodhi.fedoraproject.org/releases/?exclude_archived=true'
    releases["fedora"] = {}

    # use curl for robustness
    output = subprocess.check_output(
        ['curl', '--silent', '--show-error', '--fail', '--retry', '5', '--max-time', '10', url],
        text=True
    )

    data = json.loads(output)
    fedora_releases_list = [r for r in data['releases'] if r['id_prefix'] == 'FEDORA']
    for release in fedora_releases_list:
        releases['fedora'][release['branch']] = release['dist_tag']

    with open(RELEASES_JSON, 'w') as f:
        json.dump(releases, f, indent=2, sort_keys=True)
        f.write('\n')

    logging.info("Updated upstream-releases.json")


def update_package_overrides(original_name: str, new_name: str) -> None:
    """Update package name in package-overrides.yaml."""
    with open(PACKAGE_OVERRIDES_YAML, 'r') as f:
        overrides = yaml.safe_load(f) or {}
    if original_name in overrides:
        # Rename the key while preserving order
        overrides[new_name] = overrides.pop(original_name)
        with open(PACKAGE_OVERRIDES_YAML, 'w') as f:
            yaml.dump(overrides, f, default_flow_style=False, sort_keys=False)
        logging.info(f"Renamed {original_name} to {new_name} in {PACKAGE_OVERRIDES_YAML}")


def update_rename_record(old: str, new: str) -> None:
    """Record a package rename in renamed_packages.json."""
    # Load existing rename records
    renames = {}
    if RENAMED_PACKAGES_JSON.exists():
        with open(RENAMED_PACKAGES_JSON, 'r') as f:
            renames = json.load(f)

        if new in renames:
            logging.info(f"Package '{new}' already exists in rename records (was renamed from '{renames[new]}')")
            return

    renames[new] = old

    with open(RENAMED_PACKAGES_JSON, 'w') as f:
        json.dump(renames, f, indent=2, sort_keys=True)
        f.write('\n')  # Ensure trailing newline

    logging.info(f"Recorded rename: {old} -> {new} in {RENAMED_PACKAGES_JSON}")


def rename(original_name: str) -> None:
    """Rename a package for RPM versioning (i.e. tomcat -> tomcat11"""

    original_dir = RPMS_DIR / original_name

    if not original_dir.exists():
        sys.exit(f"ERROR: Package directory {original_dir} does not exist")

    new_name = rename_spec_validate(original_name, original_dir)
    logging.info("Renaming package '%s' to '%s' in '%s'", original_name, new_name, RPMS_DIR)

    new_dir = RPMS_DIR / new_name
    original_metadata_file = METADATA_DIR / f'{original_name}.json'
    new_metadata_file = METADATA_DIR / f'{new_name}.json'

    if new_dir.exists():
        sys.exit(f"ERROR: Package directory {new_dir} already exists")

    if not original_metadata_file.exists():
        sys.exit(f"ERROR: Package metadata file {original_metadata_file} does not exist")

    if new_metadata_file.exists():
        sys.exit(f"ERROR: Package metadata file {new_metadata_file} already exists")


    run_git('mv', f'rpms/{original_name}', f'rpms/{new_name}', cwd=ROOT_DIR)
    logging.info(f"Successfully renamed {original_dir} to {new_dir}")
    run_git('mv', f'metadata/{original_name}.json', f'metadata/{new_name}.json', cwd=ROOT_DIR)
    logging.info(f"Successfully renamed {original_metadata_file} to {new_metadata_file}")

    update_package_overrides(original_name, new_name)
    update_rename_record(original_name, new_name)

    logging.info("Running make generate to update Tekton resources...")
    subprocess.run(['make', 'generate'], cwd=ROOT_DIR, check=True)

    # Commit the changes
    logging.info("Committing changes for rename.")
    run_git('add', '-f',
            str(PACKAGE_OVERRIDES_YAML.relative_to(ROOT_DIR)),
            str(RENAMED_PACKAGES_JSON.relative_to(ROOT_DIR)),
            'konflux-templates', '.tekton', cwd=ROOT_DIR)
    commit_msg = f"Rename {original_name} to {new_name}"
    run_git_commit('-m', commit_msg, cwd=ROOT_DIR)

    logging.info("Renaming complete")


def get_dist_tag(branch: str) -> str:
    """Get dist_tag for a branch from upstream-releases.json.

    For Fedora branches, looks up in upstream-releases.json.
    For CentOS Stream, uses direct conversion.
    """
    # Check Fedora releases first
    if branch in releases.get('fedora', {}):
        return releases['fedora'][branch]

    # CentOS Stream: c9s -> el9, c10s -> el10
    if match := re.match(r'^c(\d+)s$', branch):
        return f'el{match.group(1)}'

    sys.exit(f"ERROR: Unknown branch '{branch}'. Run 'update-releases' to refresh.")


def get_previous_fedora_release(dist_tag: str) -> str | None:
    """Get the dist_tag for the previous Fedora release.

    For a given dist_tag (e.g., f44), returns the next lower numbered release (e.g., f43).
    Returns None if no previous release found.
    Used as fallback when current build not found in Koji.
    """
    # Extract number from current dist_tag
    current_match = re.match(r'^f(\d+)$', dist_tag)
    if not current_match:
        return None  # Not a numbered release

    current_num = int(current_match.group(1))

    # Find all fNN releases less than current
    fedora_releases = releases.get('fedora', {})
    previous_releases = []
    for release_dist_tag in fedora_releases.values():
        if match := re.match(r'^f(\d+)$', release_dist_tag):
            num = int(match.group(1))
            if num < current_num:
                previous_releases.append(num)

    if not previous_releases:
        return None

    # Return highest number less than current
    return f'f{max(previous_releases)}'


class KojiTransport(xmlrpc.client.SafeTransport):
    """Custom XML-RPC transport with proxy support and bot detection bypass."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if proxy_url := os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'):
            parsed = urllib.parse.urlparse(proxy_url)
            self.proxy_host = parsed.hostname
            self.proxy_port = parsed.port or 3128
        else:
            self.proxy_host = None
            self.proxy_port = None

    def make_connection(self, host):
        if self.proxy_host:
            connection = http.client.HTTPSConnection(self.proxy_host, self.proxy_port)
            connection.set_tunnel(host)
            return connection
        else:
            # No proxy - use standard connection
            return super().make_connection(host)

    def send_headers(self, connection, headers):
        super().send_headers(connection, headers)
        # Bypass Koji's AI scraper detection
        connection.putheader("Accept", "text/xml")


def get_koji_server() -> xmlrpc.client.ServerProxy:
    """Get a Koji XML-RPC server proxy with proper transport configuration."""
    return xmlrpc.client.ServerProxy('https://koji.fedoraproject.org/kojihub',
                                      transport=KojiTransport(),
                                      allow_none=True)


class MdapiPackageInfo(TypedDict, total=False):
    """Result from MDAPI srcpkg endpoint."""
    version: str
    release: str


def get_mdapi_latest_build(package_name: str, branch: str) -> MdapiPackageInfo | None:
    """Get the latest build for a package from MDAPI.

    Queries the Fedora MDAPI (MetaSource) for package metadata.
    Returns None if no build found.
    """
    url = f'https://mdapi.fedoraproject.org/{branch}/srcpkg/{package_name}'

    try:
        output = subprocess.check_output(
            ['curl', '--silent', '--show-error', '--fail', '--retry', '3', '--max-time', '30', url],
            text=True
        )
        data = json.loads(output)
        return cast(MdapiPackageInfo, {'version': data['version'], 'release': data['release']})
    except subprocess.CalledProcessError:
        return None


def check_koji_build(package_name: str, version: str, release: str, expected_commit: str,
                     dist_tag: str, branch: str) -> bool:
    """Check if a build exists in Koji and matches the expected commit.

    If not found with current dist tag, tries the previous Fedora release as a fallback.
    """
    # Transform dist_tag for Koji: Bodhi uses f41, f42, etc. but Koji uses fc41, fc42
    koji_dist_tag = dist_tag
    if match := re.match(r'^f(\d+)$', dist_tag):
        koji_dist_tag = f'fc{match.group(1)}'

    # Construct NVR
    nvr = f'{package_name}-{version}-{release}.{koji_dist_tag}'

    server = get_koji_server()
    build_result = server.getBuild(nvr)

    # If build not found, try previous release as fallback
    # (packages are rebuilt once per release, so may still have old dist tag)
    if not build_result:
        previous_release = get_previous_fedora_release(dist_tag)
        if previous_release:
            previous_koji_dist_tag = previous_release
            if match := re.match(r'^f(\d+)$', previous_release):
                previous_koji_dist_tag = f'fc{match.group(1)}'

            fallback_nvr = f'{package_name}-{version}-{release}.{previous_koji_dist_tag}'
            logging.info("Build %s not found in Koji, trying %s", nvr, fallback_nvr)
            build_result = server.getBuild(fallback_nvr)
            if build_result:
                nvr = fallback_nvr  # Update for logging below

    if not build_result:
        logging.info("Build %s not found in Koji", nvr)
        return False

    build = cast(KojiBuild, build_result)

    # Extract commit from source field
    source = build.get('source', '')
    if '#' not in source:
        logging.warning("Build %s has no commit in source: %s", nvr, source)
        return False

    commit = source.split('#')[1]

    # Check if commit matches
    if commit != expected_commit:
        logging.warning("Build %s has different commit: %s (expected %s)",
                        nvr, commit[:8], expected_commit[:8])
        return False

    # Check build state (1 = COMPLETE)
    if build.get('state') != 1:
        logging.info("Build %s is not complete (state=%s)", nvr, build.get('state'))
        return False

    logging.info("Build %s found in Koji (commit %s)", nvr, commit[:8])
    return True


def is_package_unmodified(package_name: str, metadata: PackageMetadata, upstream_dir: Path) -> bool:
    """Check if package directory matches the imported version.

    Local changes that only affect the Release: field in the spec file
    (which we bump for rebuilds) are ignored.
    """
    package_dir = ROOT_DIR / 'rpms' / package_name

    # Clone upstream_dir as we are going to checkout specific sha and remove .git/ for comparison
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir) / package_name
        run_git('clone', '--quiet', '--branch', metadata['branch'], '--single-branch',
                str(upstream_dir), str(temp_dir))
        run_git('checkout', '--quiet', metadata['sha'], cwd=temp_dir)
        shutil.rmtree(temp_dir / '.git')

        # First, check all non-spec files are identical
        if subprocess.run(
            ['diff', '--recursive', '--ignore-trailing-space', '--ignore-blank-lines', '--exclude=*.spec', str(package_dir), str(temp_dir)],
            stdout=subprocess.DEVNULL,
        ).returncode != 0:
            return False

        # Then check including spec files, ignoring Release: lines
        # This checks all other files again, but dist-gits are small and this is very robust
        return subprocess.run(
            ['diff', '--recursive', '--ignore-trailing-space', '--ignore-blank-lines', '--ignore-matching-lines=^Release:', str(package_dir), str(temp_dir)],
            stdout=subprocess.DEVNULL,
        ).returncode == 0


def import_(url: str, branch: str, ref: str | None = None, directory: str | None = None,
            dry_run: bool = False) -> None:
    """Import a new dist-git package."""
    url = expand_url_shortcut(url)
    package_name = Path(url).stem

    # Allow overriding the directory name
    dir_name = directory if directory else package_name
    package_dir = ROOT_DIR / 'rpms' / dir_name

    if package_dir.exists():
        sys.exit(f"ERROR: Package directory rpms/{dir_name}/ already exists\n"
                 f"       Use 'sync' or 'update' command to update existing packages.")

    if dir_name != package_name:
        logging.info("Importing %s from %s to rpms/%s/ (branch: %s%s)",
                     package_name, url, dir_name, branch, f", ref: {ref}" if ref else "")
    else:
        if ref:
            logging.info("Importing %s from %s (branch: %s, ref: %s)", package_name, url, branch, ref)
        else:
            logging.info("Importing %s from %s (branch: %s)", package_name, url, branch)

    logging.info("Cloning from %s...", url)
    if ref:
        # Need full history to checkout specific ref
        run_git('clone', '--quiet', '--branch', branch, '--single-branch', url, str(package_dir))
        logging.info("Checking out ref: %s", ref)
        run_git('checkout', '--quiet', ref, cwd=package_dir)
    else:
        run_git('clone', '--quiet', '--branch', branch, '--depth=1', '--single-branch', url, str(package_dir))

    sha = run_git('rev-parse', 'HEAD', cwd=package_dir).stdout.strip()
    logging.info("Commit: %s", sha)

    # Parse spec file for version/release
    version, release = parse_spec_version(package_dir)
    logging.info("Version: %s-%s", version, release)

    # We can't have sub .git directories in our repo
    shutil.rmtree(package_dir / '.git')

    # Check if spec uses %autorelease - if so, query MDAPI for actual release
    if uses_autorelease(package_dir):
        logging.info("Upstream uses %%autorelease, querying MDAPI for latest release...")
        mdapi_build = get_mdapi_latest_build(package_name, branch)
        if mdapi_build:
            release = mdapi_build['release']
            # Strip dist suffix (e.g., "1.fc42" -> "1")
            release = re.sub(r'\.(fc|el)\d+$', '', release)
            logging.info("MDAPI latest release: %s", release)

            # Replace %autorelease in spec file with actual release value
            spec_files = list(package_dir.glob('*.spec'))
            if spec_files:
                spec_file = spec_files[0]
                spec_content = spec_file.read_text()
                new_content = re.sub(
                    r'^(Release:\s*)%\{?\??autorelease\b.*$',
                    rf'\g<1>{release}%{{?dist}}',
                    spec_content,
                    flags=re.MULTILINE
                )
                spec_file.write_text(new_content)
                logging.info("Replaced %%autorelease with %s%%{?dist} in %s", release, spec_file.name)
        else:
            logging.warning("No MDAPI build found for %s, keeping %%autorelease", package_name)

    # Save package metadata to import.json
    # The source URL contains the upstream package name, so we don't need to store it separately
    metadata: PackageMetadata = {
        'source': url,
        'branch': branch,
        'sha': sha,
        'version': version,
        'release': release,
    }
    save_package_metadata(dir_name, metadata)
    # Update global imports dict
    imports[dir_name] = metadata

    logging.info("Checking prerequisites...")
    check_jinja2_available()

    logging.info("Calling generate_resources.py to update Tekton resources...")
    subprocess.run([sys.executable, ROOT_DIR / 'ci/generate_resources.py', 'all'], check=True)

    logging.info("Successfully imported %s to rpms/%s/", package_name, dir_name)

    # Commit the changes
    if not dry_run:
        run_git('add', '-f', f'rpms/{dir_name}', f'metadata/{dir_name}.json',
                'konflux-templates', '.tekton', cwd=ROOT_DIR)
        commit_msg = f"Import {package_name}-{version}-{release}\n\nBranch: {branch}\nUpstream: {sha}"
        run_git_commit('-m', commit_msg, cwd=ROOT_DIR)


def update(package_name: str, skip_build_check: bool = False, sync: bool = False,
           dry_run: bool = False) -> None:
    """Update a single package from upstream."""
    if package_name not in imports:
        sys.exit(f"ERROR: Package {package_name} not found (missing metadata/{package_name}.json)")

    package_dir = ROOT_DIR / 'rpms' / package_name
    assert package_dir.exists()

    metadata = imports[package_name]

    # Extract the upstream package name from the source URL (for Koji queries)
    # This may differ from the directory name
    upstream_package_name = Path(metadata['source']).stem

    # Check latest commit from upstream with ls-remote (fast, no clone needed)
    result = run_git('ls-remote', metadata['source'], metadata['branch'])
    if not result.stdout.strip():
        sys.exit(f"ERROR: Unable to query remote for {package_name}")
    latest_sha = result.stdout.split()[0]

    # Check if there's an update
    if latest_sha == metadata['sha']:
        if sync:
            sys.exit(f"ERROR: Package {package_name} is already at upstream {latest_sha[:8]}")
        logging.info("Skipping %s: already up-to-date", package_name)
        return

    # There's an update available
    logging.info("Update available for %s: %s -> %s", package_name, metadata['sha'][:8], latest_sha[:8])

    with tempfile.TemporaryDirectory() as tmpdir:
        upstream_dir = Path(tmpdir) / package_name
        run_git('clone', '--quiet', '--branch', metadata['branch'], '--single-branch',
                metadata['source'], str(upstream_dir))

        # Parse spec file to get version-release
        version, release = parse_spec_version(upstream_dir)
        logging.info("Version: %s-%s", version, release)

        dist_tag = get_dist_tag(metadata['branch'])

        # Check if upstream uses %autorelease - if so, query MDAPI for actual release
        has_autorelease = uses_autorelease(upstream_dir)
        if has_autorelease:
            logging.info("Upstream uses %%autorelease, querying MDAPI for latest release...")
            mdapi_build = get_mdapi_latest_build(package_name, metadata['branch'])
            if mdapi_build:
                release = mdapi_build['release']
                # Strip dist suffix (e.g., "1.fc42" -> "1")
                release = re.sub(r'\.(fc|el)\d+$', '', release)
                logging.info("MDAPI latest release: %s", release)
            else:
                logging.warning("No MDAPI build found for %s, using spec release: %s",
                               upstream_package_name, release)
                has_autorelease = False  # Don't replace if we couldn't get MDAPI release

        # Check if this version-release was built in Koji; syncing is a human thing,
        # assume they know what they are doing
        if not skip_build_check and not sync:
            logging.info("Checking Koji for build %s-%s-%s...", upstream_package_name, version, release)
            if not check_koji_build(upstream_package_name, version, release, latest_sha, dist_tag, metadata['branch']):
                logging.info("Skipping %s: %s-%s not built in Koji", package_name, version, release)
                return

        # Check if local package has modifications (only in update mode)
        if not sync and not is_package_unmodified(package_name, metadata, upstream_dir):
            logging.info("Skipping %s: package has local modifications", package_name)
            return

        # Update is available and conditions met - apply it
        action = "Syncing" if sync else "Updating"
        logging.info("%s %s: %s -> %s", action, package_name, metadata['sha'][:8], latest_sha[:8])
        shutil.rmtree(package_dir)
        shutil.rmtree(upstream_dir / '.git')
        shutil.copytree(upstream_dir, package_dir)

        # Replace %autorelease with actual release value from MDAPI
        if has_autorelease:
            spec_files = list(package_dir.glob('*.spec'))
            if spec_files:
                spec_file = spec_files[0]
                spec_content = spec_file.read_text()
                # Replace %autorelease (with optional braces/options) with release + %{?dist}
                new_content = re.sub(
                    r'^(Release:\s*)%\{?\??autorelease\b.*$',
                    rf'\g<1>{release}%{{?dist}}',
                    spec_content,
                    flags=re.MULTILINE
                )
                spec_file.write_text(new_content)
                logging.info("Replaced %%autorelease with %s%%{?dist} in %s", release, spec_file.name)

        logging.info("Updated to %s-%s", version, release)

        # Update package metadata
        imports[package_name]['sha'] = latest_sha
        imports[package_name]['version'] = version
        imports[package_name]['release'] = release
        save_package_metadata(package_name, imports[package_name])

        # Commit the changes
        if not dry_run:
            run_git('add', '-f', f'rpms/{package_name}', f'metadata/{package_name}.json', cwd=ROOT_DIR)
            verb = "Sync" if sync else "Update"
            commit_msg = f"{verb} {upstream_package_name} to {version}-{release}\n\nUpstream: {latest_sha}"
            run_git_commit('-m', commit_msg, cwd=ROOT_DIR)


def check_git_config() -> None:
    """Check that git user.name and user.email are configured."""

    name_result = run_git('config', 'user.name', cwd=ROOT_DIR, check=False)
    email_result = run_git('config', 'user.email', cwd=ROOT_DIR, check=False)

    if (name_result.returncode != 0 or not name_result.stdout.strip() or
        email_result.returncode != 0 or not email_result.stdout.strip()):
        sys.exit(
            "ERROR: Please configure git:\n"
            "   git config user.name 'Your Name'\n"
            "   git config user.email 'you@example.com'"
        )


def main() -> None:
    global imports, releases

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Load all package metadata from per-package import.json files
    imports = get_all_imported_packages()

    # Load upstream-releases.json
    releases = cast(dict[str, dict[str, str]], json.loads(RELEASES_JSON.read_text()))

    parser = argparse.ArgumentParser(
        description='Import and sync dist-git packages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import bash from rawhide (using shortcut)
  %(prog)s import fedora/bash

  # Import tomcat from rawhide into rpms/tomcat10/ directory
  %(prog)s import --directory tomcat10 fedora/tomcat

  # Import glibc from Fedora 42 (using full URL), don't commit the update
  %(prog)s --dry-run import --branch f42 https://src.fedoraproject.org/rpms/glibc.git

  # Import from CentOS Stream
  %(prog)s import --branch c10s https://gitlab.com/redhat/centos-stream/rpms/kernel.git
"""
    )

    parser.add_argument('--dry-run', action='store_true',
                        help='Do not commit changes to git')
    parser.add_argument('-s', '--sign-off', action='store_true',
                        help='Add Signed-off-by trailer to commit messages')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # import command
    import_parser = subparsers.add_parser('import', help='Import a new dist-git package')
    import_parser.add_argument('url', help='dist-git repository URL or shortcut (e.g., fedora/bash)')
    import_parser.add_argument('--branch', default='rawhide',
                               help='Branch to import from (default: rawhide)')
    import_parser.add_argument('--ref',
                               help='Specific commit/tag to import (default: latest on branch)')
    import_parser.add_argument('--directory',
                               help='Directory name in rpms/ (default: package name from URL)')

    # update command
    update_parser = subparsers.add_parser('update', help='Update packages from upstream if unmodified')
    update_parser.add_argument('package', nargs='?', default=None,
                              help='Package name to update (default: all packages)')
    update_parser.add_argument('--skip-build-check', action='store_true',
                              help='Skip Koji build verification (for testing)')

    # sync command
    sync_parser = subparsers.add_parser('sync', help='Force-sync package to upstream (discards local changes)')
    sync_parser.add_argument('package', help='Package name to sync')

    # update-releases command
    subparsers.add_parser('update-releases', help='Update upstream-releases.json')

    # rename command
    rename_parser = subparsers.add_parser('rename', help='Rename a package')
    rename_parser.add_argument('package', help='Current package name (new name will be read from spec file)')

    args = parser.parse_args()

    # Set global sign-off flag
    global sign_off
    sign_off = args.sign_off

    # Reject --dry-run with rename (rename doesn't support dry-run)
    if args.command == 'rename' and args.dry_run:
        sys.exit("ERROR: --dry-run is not supported with the rename command")

    # Check git config for commands that will commit
    if not args.dry_run or args.command == 'rename':
        check_git_config()

    match args.command:
        case 'import':
            import_(args.url, args.branch, args.ref, args.directory, args.dry_run)
        case 'update':
            packages = [args.package] if args.package else list(imports.keys())
            for pkg in packages:
                update(pkg, args.skip_build_check, dry_run=args.dry_run)
        case 'sync':
            update(args.package, sync=True, dry_run=args.dry_run)
        case 'update-releases':
            update_releases()
        case 'rename':
            rename(args.package)


if __name__ == '__main__':
    main()
