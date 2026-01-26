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

# Packages to exclude from output (e.g., packages that should never be imported)
BLOCKLIST=(
    "fedora-release"
)

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

# Check for required commands
check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "Error: Required command '$1' is not installed." >&2
        echo "Please install it and try again." >&2
        exit 1
    fi
}

# Filter out blocklisted packages from a newline-separated list
filter_blocklist() {
    local input="$1"
    if [[ -z "${input}" ]] || [[ ${#BLOCKLIST[@]} -eq 0 ]]; then
        echo "${input}"
        return
    fi
    # Create a pattern for grep -Ev
    local pattern
    pattern=$(printf '%s\n' "${BLOCKLIST[@]}" | paste -sd'|')
    echo "${input}" | grep -Ev "^(${pattern})$" || true
}

check_command yq
if [[ "${CHECK_BUILDDEPS}" == true ]]; then
    check_command rpmspec
    check_command dnf
fi

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

# Convert binary package names to source RPM names
# Takes a newline-separated list of binary packages on stdin
# Outputs unique source RPM names (packages not found are marked with "(source unknown)")
binary_to_srpm_names() {
    local packages=()
    local pkg

    # Read all packages into an array
    while IFS= read -r pkg; do
        [[ -z "${pkg}" ]] && continue
        packages+=("${pkg}")
    done

    if [[ ${#packages[@]} -eq 0 ]]; then
        return
    fi

    # Query packages in batches to avoid ARG_MAX limits
    # Output format: "binary_name sourcerpm_filename" for each match
    # Use %{sourcerpm} since %{source_name} isn't available in all dnf versions
    local dnf_output
    dnf_output=$(printf '%s\n' "${packages[@]}" | xargs -n 200 dnf repoquery --qf '%{name} %{sourcerpm}\n' 2>/dev/null | grep -v '^$')

    # Extract source package name from sourcerpm filename (e.g., "valgrind-3.19.0-1.fc38.src.rpm" -> "valgrind")
    # The sourcerpm format is: name-version-release.src.rpm
    # We strip from the last occurrence of "-[0-9]" onwards to get just the name
    echo "${dnf_output}" | awk 'NF>=2 {print $2}' | sed -E 's/-[0-9][^-]*-[^-]*\.src\.rpm$//' | sort -u

    # Find packages that didn't match by comparing input to output
    local matched_binaries
    matched_binaries=$(echo "${dnf_output}" | awk 'NF>=2 {print $1}' | sort -u)

    # For unmatched packages, try "dnf provides" to find the real package name
    local unmatched
    # shellcheck disable=SC2312
    unmatched=$(comm -23 <(printf '%s\n' "${packages[@]}" | sort -u) <(echo "${matched_binaries}"))

    if [[ -n "${unmatched}" ]]; then
        # Collect provider package names for unmatched packages
        local providers=()
        local still_unknown=()
        local pkg provider_pkg

        while IFS= read -r pkg; do
            [[ -z "${pkg}" ]] && continue
            # dnf provides output format: "package-version.arch : Description"
            # Extract just the package name (first field, strip version-release.arch)
            provider_pkg=$(dnf provides "${pkg}" 2>/dev/null | grep -v "^Last metadata" | head -1 | awk -F: '{print $1}' | sed -E 's/-[0-9][^-]*-[^-]*\.[^.]+$//' | xargs)
            if [[ -n "${provider_pkg}" && "${provider_pkg}" != "${pkg}" ]]; then
                providers+=("${provider_pkg}")
            else
                still_unknown+=("${pkg}")
            fi
        done <<< "${unmatched}"

        # Query the provider packages for their SRPMs
        if [[ ${#providers[@]} -gt 0 ]]; then
            printf '%s\n' "${providers[@]}" | sort -u | xargs -n 200 dnf repoquery --qf '%{name} %{sourcerpm}\n' 2>/dev/null | \
                grep -v '^$' | awk 'NF>=2 {print $2}' | sed -E 's/-[0-9][^-]*-[^-]*\.src\.rpm$//' | sort -u
        fi

        # Output packages that are still unknown
        for pkg in "${still_unknown[@]}"; do
            echo "${pkg} (source unknown)"
        done
    fi
}

# Find missing packages
lockfile_srpms=$(get_lockfile_srpms | sort -u)
imported_packages=$(get_imported_packages)

missing=$(comm -23 <(echo "${lockfile_srpms}") <(echo "${imported_packages}"))
missing=$(filter_blocklist "${missing}")

# Get missing build dependencies if requested
missing_builddeps=""
if [[ "${CHECK_BUILDDEPS}" == true ]]; then
    all_buildrequires=$(get_all_buildrequires)
    # Find BuildRequires that are not in the imported packages list
    missing_binary_deps=$(comm -23 <(echo "${all_buildrequires}") <(echo "${imported_packages}"))
    # Convert binary package names to source RPM names
    if [[ -n "${missing_binary_deps}" ]]; then
        missing_builddeps=$(echo "${missing_binary_deps}" | binary_to_srpm_names)
        # Filter out SRPMs that are already imported
        # shellcheck disable=SC2312
        missing_builddeps=$(comm -23 <(echo "${missing_builddeps}" | sort -u) <(echo "${imported_packages}"))
        missing_builddeps=$(filter_blocklist "${missing_builddeps}")
    fi
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
