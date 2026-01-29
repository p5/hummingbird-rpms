#!/usr/bin/env python3
"""
Split import.json into per-package metadata files.

This script reads import.json and creates metadata/<package_name>.json
for each package.
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
IMPORT_JSON = ROOT_DIR / 'import.json'
RPMS_DIR = ROOT_DIR / 'rpms'
METADATA_DIR = ROOT_DIR / 'metadata'


def main():
    # Load import.json
    if not IMPORT_JSON.exists():
        sys.exit(f"ERROR: {IMPORT_JSON} not found")

    with open(IMPORT_JSON) as f:
        imports = json.load(f)

    print(f"Found {len(imports)} packages in import.json")

    # Create metadata directory if it doesn't exist
    METADATA_DIR.mkdir(exist_ok=True)

    created = 0
    skipped = 0
    missing_dir = 0

    for package_name, metadata in sorted(imports.items()):
        package_dir = RPMS_DIR / package_name
        metadata_file = METADATA_DIR / f'{package_name}.json'

        if not package_dir.exists():
            print(f"WARNING: Package directory {package_dir} does not exist, skipping {package_name}")
            missing_dir += 1
            continue

        if metadata_file.exists():
            print(f"WARNING: {metadata_file} already exists, skipping {package_name}")
            skipped += 1
            continue

        # Write metadata file
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
            f.write('\n')  # Ensure trailing newline

        created += 1

    print("\nSummary:")
    print(f"  Created: {created} metadata files")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  Skipped (missing directory): {missing_dir}")


if __name__ == '__main__':
    main()
