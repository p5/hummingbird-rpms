#!/usr/bin/env python3
"""
Migration script to add modification_status to all metadata files.

This script:
1. Scans all metadata/*.json files
2. For each package, determines if it's clean, modified, or native
3. Updates metadata with modification_status field
4. Creates metadata for native packages that don't have metadata files yet
"""

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Literal

# Import from dist_git.py
sys.path.insert(0, str(Path(__file__).parent))
from dist_git import (
    METADATA_DIR,
    RPMS_DIR,
    PackageMetadata,
    is_package_unmodified,
    run_git,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def is_native_package(source_url: str) -> bool:
    """Check if package is a Hummingbird-native package."""
    return 'gitlab.com/redhat/hummingbird' in source_url


def find_packages_without_metadata() -> list[str]:
    """Find packages in rpms/ that don't have metadata files."""
    all_packages = {p.name for p in RPMS_DIR.iterdir() if p.is_dir()}
    packages_with_metadata = {p.stem for p in METADATA_DIR.glob('*.json')}
    return sorted(all_packages - packages_with_metadata)


def get_package_version_release(package_name: str) -> tuple[str, str]:
    """Extract version and release from package spec file."""
    from specfile import Specfile

    spec_files = list((RPMS_DIR / package_name).glob('*.spec'))
    if not spec_files:
        logging.warning(f"No spec file found for {package_name}")
        return "unknown", "1"

    spec = Specfile(spec_files[0])
    version = spec.expand(spec.version)
    release = spec.expand(spec.raw_release)

    # Strip dist suffix (e.g., "1%{?dist}" -> "1")
    import re
    release = re.sub(r'%\{\?dist\}$', '', release)

    return version, release


def create_native_metadata(package_name: str) -> PackageMetadata:
    """Create metadata for a native Hummingbird package."""
    version, release = get_package_version_release(package_name)

    metadata: PackageMetadata = {
        "version": version,
        "release": release,
        "modification_status": "native",
    }

    return metadata


def migrate_metadata_file(metadata_path: Path, dry_run: bool = False) -> tuple[str, str]:
    """
    Add modification_status to a metadata file.

    Returns: (package_name, status) tuple
    """
    package_name = metadata_path.stem

    with open(metadata_path) as f:
        metadata: PackageMetadata = json.load(f)

    # Skip if already has modification_status
    if 'modification_status' in metadata:
        return package_name, metadata['modification_status']

    # Determine status
    status: Literal["clean", "modified", "native"]
    if is_native_package(metadata['source']):
        status = 'native'
        logging.info(f"{package_name}: Native package")
    else:
        # Check if package has modifications
        # Clone upstream to temp directory for comparison
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                upstream_dir = Path(tmpdir) / 'upstream'

                logging.info(f"{package_name}: Cloning {metadata['source']} at {metadata['branch']}...")
                run_git('clone', '--quiet', '--branch', metadata['branch'],
                       '--single-branch', metadata['source'], str(upstream_dir))

                logging.info(f"{package_name}: Checking if modified...")
                if is_package_unmodified(package_name, metadata, upstream_dir):
                    status = 'clean'
                    logging.info(f"{package_name}: Clean (unmodified)")
                else:
                    status = 'modified'
                    logging.warning(f"{package_name}: Modified (has local changes)")
        except Exception as e:
            logging.error(f"{package_name}: Error checking modification status: {e}")
            logging.warning(f"{package_name}: Defaulting to 'modified' due to error")
            status = 'modified'

    # Update metadata
    metadata['modification_status'] = status
    if status == 'modified':
        metadata['modification_reason'] = 'Pre-existing modification - requires review'

    # Write back to file
    if not dry_run:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            f.write('\n')  # Add trailing newline

    return package_name, status


def migrate_all(dry_run: bool = False):
    """Migrate all metadata files and create missing ones."""

    stats: dict[str, list[str]] = {
        'clean': [],
        'modified': [],
        'native': [],
    }

    # Migrate existing metadata files
    logging.info("Migrating existing metadata files...")
    metadata_files = sorted(METADATA_DIR.glob('*.json'))
    total = len(metadata_files)

    for i, metadata_path in enumerate(metadata_files, 1):
        logging.info(f"[{i}/{total}] Processing {metadata_path.stem}...")
        package_name, status = migrate_metadata_file(metadata_path, dry_run)
        stats[status].append(package_name)

    # Create metadata for packages without metadata
    logging.info("\nCreating metadata for native packages without metadata...")
    packages_without_metadata = find_packages_without_metadata()

    for package_name in packages_without_metadata:
        logging.info(f"Creating metadata for {package_name}...")
        metadata = create_native_metadata(package_name)

        if not dry_run:
            metadata_path = METADATA_DIR / f"{package_name}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                f.write('\n')

        stats['native'].append(package_name)

    # Print summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"\nClean packages (unmodified): {len(stats['clean'])}")
    print(f"Modified packages: {len(stats['modified'])}")
    print(f"Native packages: {len(stats['native'])}")
    print(f"\nTotal packages: {sum(len(v) for v in stats.values())}")

    if stats['modified']:
        print("\n" + "-" * 60)
        print("MODIFIED PACKAGES (require review):")
        print("-" * 60)
        for pkg in sorted(stats['modified']):
            print(f"  - {pkg}")

    if stats['native']:
        print("\n" + "-" * 60)
        print("NATIVE PACKAGES:")
        print("-" * 60)
        for pkg in sorted(stats['native']):
            print(f"  - {pkg}")

    if dry_run:
        print("\n" + "!" * 60)
        print("DRY RUN - No files were modified")
        print("Run without --dry-run to apply changes")
        print("!" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Migrate metadata files to include modification_status'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    try:
        migrate_all(dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\nMigration interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
