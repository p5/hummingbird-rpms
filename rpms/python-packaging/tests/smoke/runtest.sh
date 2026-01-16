#!/bin/bash
set -eux

# Currently there is no easy way to see the versions of installed packages.
# Let's list them to make sure we're testing against the correct package set.
rpm -qa | sort
python3 -c 'import packaging'
python3 -c 'from packaging import version; version.Version("2.5.1rc2")'
python3 -c 'from packaging import specifiers; specifiers.SpecifierSet("~=1.0")'
python3 -c 'from packaging import markers; markers.Marker("python_version>'"'"'2'"'"'")'
python3 -c 'from packaging import requirements; requirements.Requirement('"'"'name[foo]>=2,<3; python_version>"2.0"'"'"')'
python3 -c 'from packaging import tags; tags.Tag("py39", "none", "any")'
python3 -c 'from packaging.utils import canonicalize_name; canonicalize_name("Django_foobar")'
