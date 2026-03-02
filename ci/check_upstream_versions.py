#!/usr/bin/env python3
"""
Check for available upstream version updates using release-monitoring.org.

This script queries release-monitoring.org (Anitya) to check if there are
newer versions available for RPM packages in the repository. It can also
update the spec files to the new version.

Usage:
    # Check all packages
    ./ci/check_upstream_versions.py

    # Check specific packages
    ./ci/check_upstream_versions.py curl openssl gnutls

    # Show all packages (including up-to-date ones)
    ./ci/check_upstream_versions.py --all

    # Output as JSON
    ./ci/check_upstream_versions.py --json

    # Update spec files to new versions
    ./ci/check_upstream_versions.py --update curl gnutls
"""

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Try to import rpm for version comparison; fall back to packaging if unavailable
try:
    import rpm  # type: ignore[import-untyped]

    HAS_RPM = True
except ImportError:
    HAS_RPM = False
    from packaging.version import Version, InvalidVersion

ROOT_DIR = Path(__file__).resolve().parent.parent
RPMS_DIR = ROOT_DIR / "rpms"
METADATA_DIR = ROOT_DIR / "metadata"

# release-monitoring.org API base URL
ANITYA_API_BASE = "https://release-monitoring.org/api"
UPLOAD_SCRIPT = ROOT_DIR / "ci" / "upload-to-lookaside-cache.sh"

# Rate limiting: delay between API requests (in seconds)
API_DELAY = 0.2

# Default distribution to look up packages
DEFAULT_DISTRO = "Fedora"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Global sign-off flag, set from command line
sign_off: bool = False


def run_git(
    *args: str, cwd: Path | str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, stdout=subprocess.PIPE, text=True
    )


def run_git_commit(
    *args: str, cwd: Path | str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run git commit with optional --signoff flag."""
    commit_args = ["commit"]
    if sign_off:
        commit_args.append("--signoff")
    commit_args.extend(args)
    return run_git(*commit_args, cwd=cwd)


@dataclass
class VersionCheckResult:
    """Result of checking a package's upstream version."""

    package: str
    current_version: str
    upstream_version: Optional[str]
    has_update: bool
    error: Optional[str] = None
    anitya_project_id: Optional[int] = None
    updated: bool = False
    update_error: Optional[str] = None
    downloaded_sources: Optional[list[str]] = None


def compare_versions(current: str, upstream: str) -> int:
    """
    Compare two version strings.

    Returns:
        1 if upstream is newer than current
        0 if versions are equal
        -1 if current is newer than upstream
    """
    if HAS_RPM:
        # Use RPM's labelCompare for accurate comparison
        # labelCompare takes (epoch, version, release) tuples
        # We use epoch 0 and release 1 as placeholders
        result = rpm.labelCompare(("0", current, "1"), ("0", upstream, "1"))
        # labelCompare returns: 1 if first > second, 0 if equal, -1 if first < second
        # We want: 1 if upstream > current, so invert the result
        return -result
    else:
        # Fall back to packaging library
        try:
            v_current = Version(current)
            v_upstream = Version(upstream)
            if v_upstream > v_current:
                return 1
            elif v_upstream == v_current:
                return 0
            else:
                return -1
        except InvalidVersion:
            # If versions can't be parsed, do string comparison
            if upstream > current:
                return 1
            elif upstream == current:
                return 0
            else:
                return -1


def parse_spec_version(package_dir: Path) -> Optional[str]:
    """Extract version from package's spec file using rpmspec."""
    spec_files = list(package_dir.glob("*.spec"))
    if len(spec_files) != 1:
        return None

    spec_file = spec_files[0]
    try:
        result = subprocess.run(
            [
                "rpmspec",
                "-q",
                "--qf",
                "%{VERSION}\n",
                "--define=dist %{nil}",
                f"--define=_sourcedir {package_dir}",
                "--srpm",
                str(spec_file),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        version = result.stdout.strip().split("\n")[0]
        return version if version else None
    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        logger.debug(f"Error parsing spec for {package_dir.name}: {e}")
        return None


def get_package_metadata(package: str) -> Optional[dict]:
    """Get full metadata dict from metadata JSON file."""
    metadata_file = METADATA_DIR / f"{package}.json"
    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_version_from_metadata(package: str) -> Optional[str]:
    """Get version from metadata JSON file."""
    data = get_package_metadata(package)
    if data is None:
        return None
    return data.get("version")


def _get_spec_source_urls(spec_path: str, sourcedir: str) -> dict[int, str]:
    """
    Get expanded source URLs from a spec file.

    Returns a dict mapping source number to expanded URL/location.
    Only includes sources that are URLs (http/https/ftp).
    """
    from specfile import Specfile

    spec = Specfile(spec_path, sourcedir=sourcedir)
    sources = {}
    with spec.sources() as src_list:
        for src in src_list:
            loc = src.expanded_location
            if loc.startswith(("http://", "https://", "ftp://")):
                sources[src.number] = loc
    return sources


def _parse_sources_file(sources_path: Path) -> list[dict]:
    """
    Parse a dist-git 'sources' file.

    Each line has format: ALGO (filename) = hash

    Returns a list of dicts with keys: algo, filename, hash, line.
    """
    entries: list[dict[str, str]] = []
    if not sources_path.exists():
        return entries

    for line in sources_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(\w+)\s+\((.+?)\)\s+=\s+(\w+)$", line)
        if match:
            entries.append(
                {
                    "algo": match.group(1),
                    "filename": match.group(2),
                    "hash": match.group(3),
                    "line": line,
                }
            )
    return entries


def _write_sources_file(sources_path: Path, entries: list[dict]) -> None:
    """Write entries back to a dist-git 'sources' file."""
    lines = [f"{e['algo']} ({e['filename']}) = {e['hash']}" for e in entries]
    sources_path.write_text("\n".join(lines) + "\n")


def _compute_file_hash(filepath: Path, algo: str = "SHA512") -> str:
    """Compute hash of a file."""
    h = hashlib.new(algo.lower())
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(url: str, dest: Path) -> None:
    """Download a file from a URL to a local path."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "hummingbird-rpms-version-checker/1.0"}
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)


def _upload_to_lookaside(
    filepath: Path, package: str, hashtype: str = "sha512"
) -> None:
    """Upload a file to the lookaside cache using upload-to-lookaside-cache.sh."""
    if not UPLOAD_SCRIPT.exists():
        raise FileNotFoundError(f"Upload script not found: {UPLOAD_SCRIPT}")
    result = subprocess.run(
        [
            str(UPLOAD_SCRIPT),
            "-f",
            str(filepath),
            "-p",
            package,
            "-t",
            hashtype.lower(),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Lookaside upload failed (exit {result.returncode}): {stderr}"
        )
    logger.info(f"{package}: uploaded {filepath.name} to lookaside cache")


def download_new_sources(
    package: str,
    old_version: str,
    new_version: str,
) -> list[str]:
    """
    Download new source archives after a version update.

    For each Source/Source0/... in the spec that is a URL containing the
    old version, check if its filename appears in the 'sources' file.
    If it does, construct the new URL (by re-reading the spec after the
    version update), download the new source, compute its hash, and
    update the 'sources' file.

    Args:
        package: Package name
        old_version: Version before the spec update
        new_version: Version after the spec update

    Returns:
        List of downloaded filenames
    """
    package_dir = RPMS_DIR / package
    spec_files = list(package_dir.glob("*.spec"))
    if len(spec_files) != 1:
        return []

    sources_path = package_dir / "sources"
    sources_entries = _parse_sources_file(sources_path)
    sources_filenames = {e["filename"] for e in sources_entries}

    # The spec has already been updated to new_version at this point.
    # Get the new expanded source URLs from the updated spec.
    new_source_urls = _get_spec_source_urls(str(spec_files[0]), str(package_dir))

    # Build old filename -> new URL mapping.
    # For each source URL that contains the new version, derive what the
    # old filename would have been and check if it was in the sources file.
    downloaded = []
    for src_num, new_url in new_source_urls.items():
        new_filename = os.path.basename(new_url)

        # Derive what the old filename was by replacing new_version
        # with old_version in the filename
        old_filename = new_filename.replace(new_version, old_version)

        # Only process if the old filename was in the sources file
        # and the filename actually changed (contains the version)
        if old_filename == new_filename:
            continue
        if old_filename not in sources_filenames:
            continue

        logger.debug(f"{package}: Source{src_num}: {old_filename} -> {new_filename}")

        # Download the new source
        dest = package_dir / new_filename
        try:
            logger.info(f"{package}: downloading {new_url}")
            _download_file(new_url, dest)
        except Exception as e:
            logger.error(f"{package}: failed to download {new_url}: {e}")
            # Clean up partial download
            dest.unlink(missing_ok=True)
            continue

        # Upload to lookaside cache
        old_entry = next(e for e in sources_entries if e["filename"] == old_filename)
        algo = old_entry["algo"]
        try:
            _upload_to_lookaside(dest, package, algo)
        except Exception as e:
            logger.error(
                f"{package}: failed to upload {new_filename} to lookaside cache: {e}"
            )
            # Continue anyway — the file is downloaded, just not uploaded

        # Compute hash and update the sources entry
        new_hash = _compute_file_hash(dest, algo)
        old_entry["filename"] = new_filename
        old_entry["hash"] = new_hash

        downloaded.append(new_filename)

        # Remove old source file if it exists and is different
        if old_filename != new_filename:
            old_file = package_dir / old_filename
            if old_file.exists():
                old_file.unlink()
                logger.debug(f"{package}: removed old source {old_filename}")

    # Write updated sources file if anything changed
    if downloaded:
        _write_sources_file(sources_path, sources_entries)

    return downloaded


def _update_gitignore(package_dir: Path, filenames: list[str]) -> None:
    """Add filenames to .gitignore in the package directory.

    Ensures that files uploaded to the lookaside cache are not
    tracked by git.
    """
    gitignore_path = package_dir / ".gitignore"

    existing_lines: set[str] = set()
    if gitignore_path.exists():
        existing_lines = set(gitignore_path.read_text().splitlines())

    new_entries = []
    for filename in filenames:
        entry = filename
        if entry not in existing_lines:
            new_entries.append(entry)

    if new_entries:
        with open(gitignore_path, "a") as f:
            for entry in new_entries:
                f.write(f"{entry}\n")
        logger.info(
            f"{package_dir.name}: added {len(new_entries)} "
            f"file(s) to .gitignore"
        )


def mark_package_modified(package: str, reason: str) -> None:
    """
    Mark a package's metadata as modified.

    Sets modification_status to "modified" to indicate the package was
    updated from an upstream release. This blocks automatic dist-git
    updates until the package is manually marked as clean.

    Args:
        package: Package name
        reason: Reason for the update
    """
    metadata_file = METADATA_DIR / f"{package}.json"
    if not metadata_file.exists():
        logger.warning(
            f"{package}: no metadata file found, skipping modification tracking"
        )
        return

    try:
        with open(metadata_file) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"{package}: failed to read metadata: {e}")
        return

    data["modification_status"] = "modified"
    data["modification_reason"] = reason

    try:
        with open(metadata_file, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
    except OSError as e:
        logger.error(f"{package}: failed to write metadata: {e}")
        return

    logger.info(f"{package}: marked as modified in metadata")


def update_spec_version(package: str, new_version: str) -> list[str]:
    """
    Update the spec file for a package to a new version and download
    new source archives.

    - Sets Version to new_version
    - Resets Release to 0.1 (unless %autorelease is used)
    - Adds a %changelog entry (unless %autochangelog is used)
    - Downloads new source archives and updates the sources file
    - Marks the package metadata as modified

    Returns:
        List of downloaded source filenames

    Raises:
        FileNotFoundError: If spec file is not found
        Exception: On specfile library errors
    """
    from specfile import Specfile

    package_dir = RPMS_DIR / package
    spec_files = list(package_dir.glob("*.spec"))
    if len(spec_files) != 1:
        raise FileNotFoundError(
            f"Expected exactly one .spec file in {package_dir}, found {len(spec_files)}"
        )

    spec_file = spec_files[0]
    spec = Specfile(str(spec_file), sourcedir=str(package_dir))

    old_version = spec.version

    if spec.has_autorelease:
        # With autorelease, only update the version tag; release is automatic
        spec.update_version(new_version)
    else:
        # Use Release 0.1 so that when the same version is later imported
        # from Fedora (with Release >= 1), it sorts higher and replaces
        # this locally-built version.
        spec.set_version_and_release(new_version, "0.1")

    # Add changelog entry (no-op if %autochangelog is used)
    spec.add_changelog_entry(
        f"Update to {new_version}",
        author="Hummingbird",
        email="hummingbird@redhat.com",
    )

    spec.save()
    logger.info(f"{package}: updated spec {old_version} -> {new_version}")

    # Download new source archives
    downloaded = download_new_sources(package, old_version, new_version)

    # Mark metadata as modified to prevent auto-updates from overwriting
    mark_package_modified(package, f"Update to upstream version {new_version}")

    return downloaded


def query_anitya(package: str, distro: str = DEFAULT_DISTRO) -> dict:
    """
    Query release-monitoring.org for package information.

    Uses the legacy API endpoint: /api/project/<distro>/<package_name>

    Returns the full API response as a dict, or raises an exception on error.
    """
    url = f"{ANITYA_API_BASE}/project/{distro}/{package}"

    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "hummingbird-rpms-version-checker/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Package not found in {distro}")
        raise
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to release-monitoring.org: {e}")


def check_package_version(
    package: str, distro: str = DEFAULT_DISTRO
) -> VersionCheckResult:
    """
    Check if a newer version is available for a package.

    Args:
        package: Package name
        distro: Distribution name (default: Fedora)

    Returns:
        VersionCheckResult with comparison details
    """
    package_dir = RPMS_DIR / package

    # Get current version from spec file or metadata
    current_version = None
    if package_dir.exists():
        current_version = parse_spec_version(package_dir)

    if not current_version:
        current_version = get_version_from_metadata(package)

    if not current_version:
        return VersionCheckResult(
            package=package,
            current_version="unknown",
            upstream_version=None,
            has_update=False,
            error="Could not determine current version",
        )

    # Query release-monitoring.org
    try:
        anitya_data = query_anitya(package, distro)
    except ValueError as e:
        return VersionCheckResult(
            package=package,
            current_version=current_version,
            upstream_version=None,
            has_update=False,
            error=str(e),
        )
    except ConnectionError as e:
        return VersionCheckResult(
            package=package,
            current_version=current_version,
            upstream_version=None,
            has_update=False,
            error=str(e),
        )
    except Exception as e:
        return VersionCheckResult(
            package=package,
            current_version=current_version,
            upstream_version=None,
            has_update=False,
            error=f"API error: {e}",
        )

    # Prefer stable_versions[0] over version field, as version can sometimes
    # contain incorrect data (e.g., development tags that aren't real releases)
    stable_versions = anitya_data.get("stable_versions", [])
    if stable_versions:
        upstream_version = stable_versions[0]
    else:
        upstream_version = anitya_data.get("version")

    if not upstream_version:
        return VersionCheckResult(
            package=package,
            current_version=current_version,
            upstream_version=None,
            has_update=False,
            error="No upstream version reported by Anitya",
            anitya_project_id=anitya_data.get("id"),
        )

    # Compare versions
    comparison = compare_versions(current_version, upstream_version)
    has_update = comparison > 0

    return VersionCheckResult(
        package=package,
        current_version=current_version,
        upstream_version=upstream_version,
        has_update=has_update,
        anitya_project_id=anitya_data.get("id"),
    )


def get_all_packages() -> list[str]:
    """Get list of all packages in the rpms directory."""
    packages = []
    for item in RPMS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            # Check if it has a spec file
            if list(item.glob("*.spec")):
                packages.append(item.name)
    return sorted(packages)


def main():
    parser = argparse.ArgumentParser(
        description="Check for upstream version updates using release-monitoring.org",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Check all packages, show only updates
  %(prog)s curl openssl       Check specific packages
  %(prog)s --all              Show all packages including up-to-date
  %(prog)s --json             Output results as JSON
  %(prog)s --json --all       JSON output with all packages
  %(prog)s --update curl      Update curl spec to new upstream version
        """,
    )
    parser.add_argument(
        "packages", nargs="*", help="Package names to check (default: all packages)"
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Show all packages, not just those with updates",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output results as JSON"
    )
    parser.add_argument(
        "--update",
        "-u",
        action="store_true",
        help="Update spec files to the new upstream version",
    )
    parser.add_argument(
        "--distro",
        "-d",
        default=DEFAULT_DISTRO,
        help=f"Distribution to look up in Anitya (default: {DEFAULT_DISTRO})",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output (implies not --verbose)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=API_DELAY,
        help=f"Delay between API requests in seconds (default: {API_DELAY})",
    )
    parser.add_argument(
        "-s",
        "--sign-off",
        action="store_true",
        help="Add Signed-off-by trailer to commit messages",
    )

    args = parser.parse_args()

    global sign_off
    sign_off = args.sign_off

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    if args.quiet:
        logger.setLevel(logging.WARNING)

    # Determine which packages to check
    if args.packages:
        packages = args.packages
    else:
        packages = get_all_packages()
        if not args.quiet:
            logger.info(f"Checking {len(packages)} packages...")

    results: list[VersionCheckResult] = []
    updates_found = 0
    errors_found = 0

    for i, package in enumerate(packages):
        if not args.quiet and not args.json:
            # Progress indicator
            print(
                f"\rChecking {i + 1}/{len(packages)}: {package:<40}", end="", flush=True
            )

        result = check_package_version(package, args.distro)
        results.append(result)

        if result.has_update:
            updates_found += 1
        if result.error:
            errors_found += 1

        # Rate limiting
        if i < len(packages) - 1:
            time.sleep(args.delay)

    # Clear progress line
    if not args.quiet and not args.json:
        print("\r" + " " * 60 + "\r", end="")

    # Update spec files if requested
    updates_applied = 0
    if args.update:
        for result in results:
            if not result.has_update or not result.upstream_version:
                continue
            try:
                downloaded = update_spec_version(
                    result.package, result.upstream_version
                )
                result.updated = True
                result.downloaded_sources = downloaded
                updates_applied += 1

                # Add downloaded sources to .gitignore so they
                # are not committed (they live in the lookaside cache)
                if downloaded:
                    _update_gitignore(RPMS_DIR / result.package, downloaded)

                # Commit the changes (no -f so .gitignore is respected)
                run_git(
                    "add",
                    f"rpms/{result.package}",
                    f"metadata/{result.package}.json",
                    cwd=ROOT_DIR,
                )
                commit_msg = (
                    f"Update {result.package} to"
                    f" {result.upstream_version}\n\n"
                    f"Upstream version detected via"
                    f" release-monitoring.org"
                )
                run_git_commit("-m", commit_msg, cwd=ROOT_DIR)
            except Exception as e:
                result.update_error = str(e)
                logger.error(f"{result.package}: failed to update spec: {e}")

    # Output results
    if args.json:
        output = {
            "total_packages": len(packages),
            "updates_available": updates_found,
            "updates_applied": updates_applied,
            "errors": errors_found,
            "results": [
                {
                    "package": r.package,
                    "current_version": r.current_version,
                    "upstream_version": r.upstream_version,
                    "has_update": r.has_update,
                    "updated": r.updated,
                    "downloaded_sources": r.downloaded_sources,
                    "error": r.error,
                    "update_error": r.update_error,
                    "anitya_project_id": r.anitya_project_id,
                }
                for r in results
                if args.all or r.has_update or r.error
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Text output
        if updates_found > 0:
            if args.update:
                print("\nPackages updated:")
                print("-" * 80)
                print(
                    f"{'Package':<30} {'Current':<15} {'Upstream':<15} {'Status':<10}"
                )
                print("-" * 80)
            else:
                print("\nPackages with available updates:")
                print("-" * 70)
                print(f"{'Package':<30} {'Current':<15} {'Upstream':<15}")
                print("-" * 70)

            for r in results:
                if r.has_update:
                    if args.update:
                        status = "UPDATED" if r.updated else "FAILED"
                        print(
                            f"{r.package:<30} {r.current_version:<15} {r.upstream_version:<15} {status}"
                        )
                        if r.downloaded_sources:
                            for src in r.downloaded_sources:
                                print(f"  -> {src}")
                        if r.update_error:
                            print(f"  Error: {r.update_error}")
                    else:
                        print(
                            f"{r.package:<30} {r.current_version:<15} {r.upstream_version:<15}"
                        )

        if args.all:
            # Show up-to-date packages
            up_to_date = [r for r in results if not r.has_update and not r.error]
            if up_to_date:
                print("\nUp-to-date packages:")
                print("-" * 70)
                for r in up_to_date:
                    print(f"{r.package:<30} {r.current_version:<15}")

        if errors_found > 0:
            print("\nPackages with errors:")
            print("-" * 70)
            for r in results:
                if r.error:
                    print(f"{r.package:<30} {r.error}")

        # Summary
        print()
        if args.update:
            update_failures = updates_found - updates_applied
            print(
                f"Summary: {updates_applied} specs updated, "
                f"{update_failures} update failures, "
                f"{len(results) - updates_found - errors_found} up-to-date, "
                f"{errors_found} errors"
            )
        else:
            print(
                f"Summary: {updates_found} updates available, "
                f"{len(results) - updates_found - errors_found} up-to-date, "
                f"{errors_found} errors"
            )

    # Exit code: 0 if no updates, 1 if updates found, 2 if errors
    if errors_found > 0 and updates_found == 0:
        sys.exit(2)
    elif updates_found > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
