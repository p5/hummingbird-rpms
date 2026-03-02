#!/usr/bin/env python3
"""
CI validation script for package modification tracking.

This script validates that the modification_status in metadata files
accurately reflects the actual state of packages.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

# Import from dist_git.py
sys.path.insert(0, str(Path(__file__).parent))
from dist_git import (
    METADATA_DIR,
    RPMS_DIR,
    ROOT_DIR,
    PackageMetadata,
    is_package_unmodified,
    run_git,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def get_changed_packages_in_mr() -> list[str]:
    """Get list of packages that were modified in the current MR/branch."""
    # Get the target branch (usually 'main')
    target_branch = os.environ.get('CI_MERGE_REQUEST_TARGET_BRANCH_NAME', 'main')

    # Get changed files in rpms/ or metadata/
    result = run_git('diff', '--name-only', f'origin/{target_branch}...HEAD', cwd=ROOT_DIR)

    changed_packages = set()
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue

        # Check if file is in rpms/ or metadata/
        if line.startswith('rpms/'):
            # Extract package name from rpms/<package>/...
            parts = line.split('/')
            if len(parts) >= 2:
                changed_packages.add(parts[1])
        elif line.startswith('metadata/') and line.endswith('.json'):
            # Extract package name from metadata/<package>.json
            package = Path(line).stem
            changed_packages.add(package)

    return sorted(changed_packages)


def validate_package(package_name: str, check_actual_state: bool = True) -> tuple[bool, str | None]:
    """
    Validate modification_status for a package.

    Args:
        package_name: Package name to validate
        check_actual_state: If True, verify actual package state matches metadata
                          (requires cloning upstream, slow)

    Returns:
        (is_valid, error_message) tuple
    """
    metadata_file = METADATA_DIR / f'{package_name}.json'
    package_dir = RPMS_DIR / package_name

    # Check that both metadata and package dir exist
    if not metadata_file.exists():
        return False, f"{package_name}: Missing metadata file"

    if not package_dir.exists():
        return False, f"{package_name}: Missing package directory"

    # Load metadata
    with open(metadata_file) as f:
        metadata: PackageMetadata = json.load(f)

    # Check 1: Field must exist
    if 'modification_status' not in metadata:
        return False, f"{package_name}: Missing modification_status field"

    status = metadata['modification_status']

    # Check 2: Must be valid value
    if status not in ['clean', 'modified', 'native']:
        return False, f"{package_name}: Invalid modification_status '{status}'"

    # Check 3: Native packages should not have source/branch/sha fields
    if status == 'native':
        if 'source' in metadata or 'branch' in metadata or 'sha' in metadata:
            return False, f"{package_name}: Native package should not have source/branch/sha fields"
        # Native packages don't need further validation
        return True, None

    # Check 4: Modified packages must have reason
    if status == 'modified' and not metadata.get('modification_reason'):
        return False, f"{package_name}: Marked as modified but missing modification_reason"

    # Check 5 & 6: Verify actual state matches metadata (if requested)
    if check_actual_state and status in ['clean', 'modified']:
        with tempfile.TemporaryDirectory() as tmpdir:
            upstream_dir = Path(tmpdir) / 'upstream'

            logging.debug(f"{package_name}: Cloning {metadata['source']} at {metadata['branch']}...")
            run_git('clone', '--quiet', '--branch', metadata['branch'],
                   '--single-branch', metadata['source'], str(upstream_dir))

            logging.debug(f"{package_name}: Checking if modified...")
            actually_unmodified = is_package_unmodified(package_name, metadata, upstream_dir)

            if status == 'clean' and not actually_unmodified:
                return False, f"{package_name}: Marked as clean but package has modifications"

            if status == 'modified' and actually_unmodified:
                return False, f"{package_name}: Marked as modified but package is actually clean"

    return True, None


def find_packages_without_metadata() -> list[str]:
    """Find packages in rpms/ that don't have metadata files."""
    all_packages = {p.name for p in RPMS_DIR.iterdir() if p.is_dir()}
    packages_with_metadata = {p.stem for p in METADATA_DIR.glob('*.json')}
    return sorted(all_packages - packages_with_metadata)


def validate_packages(packages: list[str], check_actual_state: bool = True) -> int:
    """
    Validate multiple packages.

    Returns:
        Exit code (0 = success, 1 = validation failed)
    """
    errors = []
    total = len(packages)

    for i, package_name in enumerate(packages, 1):
        logging.info(f"[{i}/{total}] Validating {package_name}...")

        valid, error = validate_package(package_name, check_actual_state)

        if not valid:
            errors.append(error)

    if errors:
        print("\n" + "=" * 60, file=sys.stderr)
        print("VALIDATION FAILED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("\n" + "=" * 60, file=sys.stderr)
        print(f"Total errors: {len(errors)}/{total}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        return 1

    print(f"\nValidation passed for all {total} package(s)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Validate package modification_status metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate packages changed in current MR (fast)
  %(prog)s --mr

  # Validate all packages (slow, checks actual state)
  %(prog)s --all

  # Validate specific packages
  %(prog)s bash glibc gcc

  # Validate without checking actual state (fast)
  %(prog)s --no-check-state --all
"""
    )

    parser.add_argument('packages', nargs='*',
                       help='Package names to validate (default: all packages)')
    parser.add_argument('--mr', action='store_true',
                       help='Validate only packages changed in current MR')
    parser.add_argument('--all', action='store_true',
                       help='Validate all packages')
    parser.add_argument('--no-check-state', action='store_true',
                       help='Skip checking actual package state (faster)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine which packages to validate
    if args.mr:
        packages = get_changed_packages_in_mr()
        if not packages:
            print("No packages changed in MR")
            return 0
        print(f"Validating {len(packages)} package(s) changed in MR:")
        for pkg in packages:
            print(f"  - {pkg}")
    elif args.all:
        # Check for packages missing metadata files
        missing_metadata = find_packages_without_metadata()
        if missing_metadata:
            print(f"\nERROR: Found {len(missing_metadata)} package(s) without metadata files:", file=sys.stderr)
            for pkg in missing_metadata:
                print(f"  - {pkg}", file=sys.stderr)
            return 1

        # Get all packages with metadata
        packages = sorted([p.stem for p in METADATA_DIR.glob('*.json')])
        print(f"Validating all {len(packages)} packages...")
    elif args.packages:
        packages = args.packages
        print(f"Validating {len(packages)} specified package(s)...")
    else:
        parser.error("Must specify --mr, --all, or package names")

    check_actual_state = not args.no_check_state

    if check_actual_state:
        print("Note: Checking actual package state (this may take a while)...")
    else:
        print("Note: Skipping actual state verification (fast mode)")

    return validate_packages(packages, check_actual_state)


if __name__ == '__main__':
    sys.exit(main())
