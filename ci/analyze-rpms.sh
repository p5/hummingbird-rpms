#!/bin/bash
# List RPMs that are required by container lockfiles but not yet imported into
# the rpms repo.  With --builddeps, it also examines BuildRequires from spec
# files to find missing build dependencies.
#
# This script compares:
#   - SRPMs listed in containers repo lockfiles (rpms.lock.yaml)
#   - Package directories already present in rpms/rpms/
#
#
# Usage: ./ci/analyze-rpms.sh [OPTIONS]
#
# Options:
#   --containers-dir DIR   Path to containers repo (default: ../containers)
#   --count                Only show the count of missing RPMs
#   --builddeps            Also list missing build dependencies from spec files
#   --help                 Show this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONTAINERS_DIR="${REPO_ROOT}/../containers"
COUNT_ONLY=false
CHECK_BUILDDEPS=false

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

List RPMs that are required by container lockfiles but not yet imported.

OPTIONS:
    --containers-dir DIR   Path to containers repo (default: ../containers)
    --count                Only show the count of missing RPMs
    --builddeps            Also list missing build dependencies from spec files
    --help, -h             Show this help message

EXAMPLES:
    $0
    $0 --count
    $0 --builddeps
    $0 --containers-dir /path/to/containers
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --containers-dir)
            CONTAINERS_DIR="$2"
            shift 2
            ;;
        --count)
            COUNT_ONLY=true
            shift
            ;;
        --builddeps)
            CHECK_BUILDDEPS=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_help >&2
            exit 1
            ;;
    esac
done

# Validate containers directory
if [[ ! -d "${CONTAINERS_DIR}" ]]; then
    echo "Error: Containers directory not found: ${CONTAINERS_DIR}" >&2
    echo "Use --containers-dir to specify the correct path" >&2
    exit 1
fi

# Validate rpms directory
RPMS_DIR="${REPO_ROOT}/rpms"
if [[ ! -d "${RPMS_DIR}" ]]; then
    echo "Error: RPMs directory not found: ${RPMS_DIR}" >&2
    exit 1
fi

# Get list of SRPMs from container lockfiles
get_lockfile_srpms() {
	(cd "${CONTAINERS_DIR}"; make list-lockfile-srpms)
}

# Get list of already imported packages
get_imported_packages() {
    find "${RPMS_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -u
}

# Extract BuildRequires from a spec file, returning just package names
# Strips version constraints like >= 1.0, parenthetical comments, etc.
get_buildrequires_from_spec() {
    local spec="$1"
    local spec_dir
    spec_dir="$(dirname "${spec}")"

    # Use rpmspec to expand the spec and extract BuildRequires
    # This handles conditionals and macros properly
    rpmspec -q --buildrequires \
        --define="dist %{nil}" \
        --define="_sourcedir ${spec_dir}" \
        "${spec}" 2>/dev/null | \
    # Extract just the package name (first field, strip version constraints)
    sed -E 's/[[:space:]]*(>=|<=|>|<|=).*//; s/\(.*\)//; s/[[:space:]]+$//' | \
    # Remove common virtual provides that aren't real packages
    # Also filter out incomplete rich dependency fragments (e.g., "if python3", "(pkg if")
    grep -Ev '^(/|pkgconfig\(|cmake\(|perl\(|python[0-9]*dist\(|rubygem\(|golang\(|npm\(|mvn\(|osgi\(|tex\(|font\(|[[:space:]]*if |[[:space:]]*\()' | \
    sort -u
}

# Get all BuildRequires from all spec files
get_all_buildrequires() {
    local spec
    # shellcheck disable=SC2312
    while IFS= read -r -d '' spec; do
        get_buildrequires_from_spec "${spec}"
    done < <(find "${RPMS_DIR}" -mindepth 2 -maxdepth 2 -name "*.spec" -type f -print0) | sort -u
}

# Find missing packages
lockfile_srpms=$(get_lockfile_srpms | sort -u)
imported_packages=$(get_imported_packages)

missing=$(comm -23 <(echo "${lockfile_srpms}") <(echo "${imported_packages}"))

# Get missing build dependencies if requested
missing_builddeps=""
if [[ "${CHECK_BUILDDEPS}" == true ]]; then
    all_buildrequires=$(get_all_buildrequires)
    # Find BuildRequires that are not in the imported packages list
    missing_builddeps=$(comm -23 <(echo "${all_buildrequires}") <(echo "${imported_packages}"))
fi

# Count non-empty lines in a string
count_lines() {
    local text="$1"
    if [[ -z "${text}" ]]; then
        echo "0"
    else
        echo "${text}" | wc -l
    fi
}

missing_count=$(count_lines "${missing}")
builddeps_count=0
if [[ "${CHECK_BUILDDEPS}" == true ]]; then
    builddeps_count=$(count_lines "${missing_builddeps}")
fi

if [[ "${COUNT_ONLY}" == true ]]; then
    if [[ "${CHECK_BUILDDEPS}" == true ]]; then
        echo "Missing from lockfiles: ${missing_count}"
        echo "Missing build dependencies: ${builddeps_count}"
    else
        echo "${missing_count}"
    fi
else
    if [[ -z "${missing}" ]]; then
        echo "All required RPMs are already imported."
    else
        echo "* Missing RPMs (identified in containers repo but not imported in rpms repo):"
        echo ""
        echo "${missing}"
        echo ""
        echo "* Total missing: ${missing_count}"
        echo ""
        echo "* To import these packages, run:"
        echo "*  ./ci/dist_git.py import fedora/<package_name>"
    fi

    if [[ "${CHECK_BUILDDEPS}" == true ]]; then
        echo ""
        echo "* =========================================="
        echo ""
        if [[ -z "${missing_builddeps}" ]]; then
            echo "All build dependencies are already imported."
        else
            echo "* Missing build dependencies (BuildRequires not in rpms repo):"
            echo ""
            echo "${missing_builddeps}"
            echo ""
            echo "* Total missing build deps: ${builddeps_count}"
            echo ""
            echo "* Note: Some may be virtual provides or available from Fedora repos."
            echo "* To import a missing dependency, run:"
            echo "*  ./ci/dist_git.py import fedora/<package_name>"
        fi
    fi
fi
