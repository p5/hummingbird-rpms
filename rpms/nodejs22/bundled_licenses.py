#!/bin/env python3

# Copyright 2024 Red Hat
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

# A Python script bundled_licenses.py should help identifying
# licenses used in the bundled deps. It simply parses package.json
# files in the given directory and returns best guess about the
# License: RPM tag.
#
# The expected usage is like this:
# * run bundled_licenses.py on the binary RPMs to see what is
#   bundled in the shipped RPMs
# * validate the output of bundled_licenses.py
# * add licenses identified in the source code of nodejs itself
# * validate the resulting License tag suggestion by license-validate tool

import argparse
import os
import json


def find_package_json(directories):
    # List to store file paths matching the pattern
    file_paths = []

    # Walk through the directories and their subdirectories
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file == 'package.json':
                    # package.json under a directory test/fixtures are usually not relevant
                    file_path = os.path.join(root, file)
                    if 'test/fixtures' in file_path:
                        print(f"Warning: Skipping {file_path} as it seems to be a fixture that is likely not valid.")
                        continue
                    print(f"Found package.json at: {file_path}")
                    file_paths.append(file_path)
    return file_paths


def parse_license_tag(license_tag):
    if type(license_tag) == dict and 'type' in license_tag:
        return license_tag['type']
    return license_tag


def fix_known_spdx_issues(license):
    if license == 'Apache 2.0':
        return 'Apache-2.0'
    return license


def license_from_package_json(file_path):
    with open(file_path, 'r') as json_file:
        try:
            data = json.load(json_file)
            if 'license' in data:
                return parse_license_tag(data['license'])
            elif 'licenses' in data:
                return ' AND '.join([parse_license_tag(license) for license in data['licenses']])
            else:
                if 'name' in data and 'version' in data:
                    print(f"Error: Key license not found in {file_path} despite it looking like a valid package.json file")
                else:
                    print(f"Warning: Key license not found in {file_path} but it might not be a valid package.json file at all")
        except json.JSONDecodeError as e:
            print(f"Error parsing {file_path}: {e}")

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Find and parse package.json '\
             'files in specified directories, and return probable License tag to '\
             'be used in an RPM spec file. It is likely better to run it on '\
             'unpacked or installed RPMs, rather than unpacked source, because '\
             'some of the bundled deps are likely not used in the shipped output. '\
             'It is always necessary to manually verify the results by investigating '\
             'the files and the resulting License tag may be verified using '\
             'license-validate tool (check license-validate RPM in Fedora) .')
    parser.add_argument('directories', nargs='*', default=[os.getcwd()], 
                        help='Directories to search for package.json files, if none is given, use the current directory.')

    args = parser.parse_args()

    licenses = set()

    package_json_files = find_package_json(args.directories)
    for f in package_json_files:
        l = license_from_package_json(f)
        if l:
            licenses.add(fix_known_spdx_issues(l))
            print(f"OK: License detected in {f}: {l}")
    print('Final license tag to be used in the RPM spec file (please, confirm manually '\
          'by looking into files and validate using the license-validate tool):')
    print('License: ' + ' AND '.join(sorted(licenses)))
