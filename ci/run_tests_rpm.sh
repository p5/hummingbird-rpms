#!/bin/bash

# Run tests for RPM packages
# Use --help for detailed usage information

set -euo pipefail
shopt -s inherit_errexit

show_help() {
    cat << EOF
Usage: $0 [OPTIONS] PACKAGE_NAME

Run tests for RPM packages.

OPTIONS:
    --rpm PATH            Path to binary RPM file to test (optional)
                          Can be specified multiple times for multiple RPMs
                          If not provided, auto-discovers RPMs from --repo-dir,
                          ./builds/<package>/RPMS/, or ./RPMS/
    --repo-dir PATH       Path to directory containing RPMs to create a local repository
                          (optional, enables dependency resolution for multi-package builds)
    --src-rpm PATH        Path to source RPM file (optional, enables source RPM tests)
    --jobs [N], -j [N]    Number of parallel RPM tests to run (default: 1)
                          If N is omitted, uses number of CPU cores
    --verbose, -v         Enable verbose output during testing
    --help, -h            Show this help message

ARGUMENTS:
    PACKAGE_NAME         Name of the RPM package (must correspond to a folder in rpms/)
                         Examples: rootfiles, setup

EXAMPLES:
    $0 --rpm /path/to/rootfiles-1.0-1.fc40.x86_64.rpm rootfiles
    $0 --rpm /path/to/setup-2.0-1.fc40.noarch.rpm --verbose setup
    $0 --rpm /path/to/setup.rpm --src-rpm /path/to/setup.src.rpm setup
    $0 --rpm /path/to/setup.fc40.rpm --rpm /path/to/setup.fc41.rpm setup
    $0 --rpm /path/to/rpm.rpm --repo-dir /path/to/RPMS/ --src-rpm /path/to/rpm.src.rpm rpm

DESCRIPTION:
    Runs default tests for the specified RPM package. Tests are defined in
    ci/default-tests/tests-rpm.yml and package-specific tests in
    test/rpms/.yml (if present).

    When multiple RPMs are specified, the same test suite is run for each RPM.
EOF
}

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
base_dir="$(dirname "${SCRIPT_DIR}")"

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
LIGHT_CYAN='\033[1;36m'
NC='\033[0m' # No Color

log_heading() { printf "${LIGHT_CYAN}=== %s ===${NC}\n" "$*" >&2; }
log_pass() { printf "  ${GREEN}[PASS]${NC} %s\n" "$*" >&2; }
log_unexpected_pass() { printf "  ${RED}[UNEXPECTED PASS]${NC} %s\n" "$*" >&2; }
log_known_failure() { printf "  ${YELLOW}[KNOWN FAILURE]${NC} %s\n" "$*" >&2; }
log_fail() { printf "  ${RED}[UNKNOWN FAILURE]${NC} %s\n" "$*" >&2; }
log_info() { printf "  %s\n" "$*" >&2; }

# Convert YAML to JSON (simple Python-based converter)
yaml_to_json() {
    python3 -c 'import sys, yaml, json; json.dump(yaml.safe_load(sys.stdin), sys.stdout)'
}

# Check if test output matches any known issues
# Returns "<issue_url>\n<description> [fails: <frequency>]" if found, empty string otherwise
check_known_issues() {
    local known_issues_json=$1 test_output_file=$2 patterns

    if [[ ${known_issues_json} != "[]" ]]; then
        patterns=$(jq -r '
            .[] |
            if (type == "object" and (.pattern | type == "array"))
                then .pattern[]
                else .pattern
            end
        ' <<< "${known_issues_json}")
        while IFS= read -r pattern; do
            if grep -qE "${pattern}" "${test_output_file}" 2>/dev/null; then
                local issue description fails_value
                known_issue_json=$(jq -c --arg pattern "${pattern}" '
                    .[] | select(
                            (.pattern == $pattern) or
                            (.pattern | type == "array" and index($pattern) != null)
                    )
                ' <<< "${known_issues_json}" | head -n1)
                issue=$(jq -r '.issue // "no-issue-url"' <<< "${known_issue_json}")
                description=$(jq -r '.description' <<< "${known_issue_json}")
                fails_value=$(jq -r '.fails // "always"' <<< "${known_issue_json}")

                # Don't include null or empty issue URLs in output
                if [[ ${issue} == "null" || ${issue} == "no-issue-url" ]]; then
                    echo ""
                    echo "${description} [fails: ${fails_value}]"
                else
                    echo "${issue}"
                    echo "${description} [fails: ${fails_value}]"
                fi
                return 0
            fi
        done <<< "${patterns}"
    fi
}

# Fail the test with a stderr message and exit code 1
TEST_FAIL() {
    echo "$1" >&2
    exit 1
}
export -f TEST_FAIL

# Parse command line arguments
TEST_VERBOSE=false
TEST_ENGINE=podman
TEST_IMAGE="${TEST_IMAGE:-quay.io/hummingbird/core-runtime:latest-builder}"
TEST_SRC_RPM=""
TEST_REPO_DIR=""
TEST_JOBS=1
RPM_PATHS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            TEST_VERBOSE=true
            shift
            ;;
        --rpm)
            RPM_PATHS+=("$2")
            shift 2
            ;;
        --repo-dir)
            TEST_REPO_DIR=$2
            shift 2
            ;;
        --src-rpm)
            TEST_SRC_RPM=$2
            shift 2
            ;;
        --jobs|-j)
            # Check if next argument is a number or missing/another option
            if [[ -z ${2:-} ]] || [[ $2 == -* ]]; then
                # No number provided, use number of CPU cores
                TEST_JOBS=$(nproc)
                shift
            elif [[ $2 =~ ^[0-9]+$ ]]; then
                TEST_JOBS=$2
                if (( TEST_JOBS < 1 )); then
                    echo "Error: --jobs must be a positive integer"
                    exit 1
                fi
                shift 2
            else
                # Next argument is not a number (probably package name), use nproc
                TEST_JOBS=$(nproc)
                shift
            fi
            ;;
        -j[0-9]*)
            # Handle -jN format (no space between -j and number)
            TEST_JOBS=${1#-j}
            if (( TEST_JOBS < 1 )); then
                echo "Error: --jobs must be a positive integer"
                exit 1
            fi
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: $0 [OPTIONS] PACKAGE_NAME"
            exit 1
            ;;
        *)
            if [[ -z ${PACKAGE_NAME:-} ]]; then
                PACKAGE_NAME=$1
            else
                echo "Error: Too many arguments"
                echo "Usage: $0 [OPTIONS] PACKAGE_NAME"
                exit 1
            fi
            shift
            ;;
    esac
done >&2

# Validate arguments
if [[ -z ${PACKAGE_NAME:-} ]]; then
    echo "Error: PACKAGE_NAME is required"
    echo "Usage: $0 [OPTIONS] PACKAGE_NAME"
    exit 1
fi >&2

# Auto-discover RPMs if none provided
if [[ ${#RPM_PATHS[@]} -eq 0 ]]; then
    # Determine search directory (check multiple locations)
    if [[ -n ${TEST_REPO_DIR} ]]; then
        search_dir="${TEST_REPO_DIR}"
    elif [[ -d "./builds/${PACKAGE_NAME}/RPMS" ]]; then
        search_dir="./builds/${PACKAGE_NAME}/RPMS"
    elif [[ -d ./RPMS ]]; then
        search_dir="./RPMS"
    else
        search_dir="."
    fi

    # Get current architecture
    current_arch=$(uname -m)

    # Find RPMs matching package name and architecture
    # shellcheck disable=SC2312
    while IFS= read -r -d '' rpm_file; do
        rpm_name=$(rpm -qp --queryformat '%{NAME}' "${rpm_file}" 2>/dev/null) || continue
        rpm_arch=$(rpm -qp --queryformat '%{ARCH}' "${rpm_file}" 2>/dev/null) || continue

        # Check if RPM name starts with package name (handles subpackages like tcl-devel)
        if [[ ${rpm_name} == "${PACKAGE_NAME}" || ${rpm_name} == "${PACKAGE_NAME}-"* ]]; then
            # Include if architecture matches or is noarch
            if [[ ${rpm_arch} == "noarch" || ${rpm_arch} == "${current_arch}" ]]; then
                RPM_PATHS+=("${rpm_file}")
            fi
        fi
    done < <(find "${search_dir}" -maxdepth 1 -name '*.rpm' ! -name '*.src.rpm' -print0 2>/dev/null)

    if [[ ${#RPM_PATHS[@]} -eq 0 ]]; then
        echo "Error: No RPMs found for package '${PACKAGE_NAME}' in ${search_dir}"
        echo "Either provide --rpm PATH or ensure RPMs exist in --repo-dir, ./builds/<package>/RPMS/, or ./RPMS/"
        exit 1
    fi

    echo "Auto-discovered ${#RPM_PATHS[@]} RPM(s) for ${PACKAGE_NAME} in ${search_dir}"
fi >&2

# Validate package directory exists
package_dir="${base_dir}/rpms/${PACKAGE_NAME}"
if [[ ! -d ${package_dir} ]]; then
    echo "Error: Package directory '${package_dir}' not found"
    exit 1
fi >&2

# Validate all RPM files exist and convert to absolute paths
for i in "${!RPM_PATHS[@]}"; do
    rpm_file="${RPM_PATHS[${i}]}"
    if [[ ! -f ${rpm_file} ]]; then
        echo "Error: RPM file '${rpm_file}' not found"
        exit 1
    fi
    # Convert to absolute path
    RPM_PATHS[i]="$(realpath "${rpm_file}")"
done >&2

# Validate source RPM file exists if provided and convert to absolute path
if [[ -n ${TEST_SRC_RPM} ]]; then
    if [[ ! -f ${TEST_SRC_RPM} ]]; then
        echo "Error: Source RPM file '${TEST_SRC_RPM}' not found"
        exit 1
    fi
    TEST_SRC_RPM=$(realpath "${TEST_SRC_RPM}")
fi >&2

# Validate repo directory exists if provided and convert to absolute path
if [[ -n ${TEST_REPO_DIR} ]]; then
    if [[ ! -d ${TEST_REPO_DIR} ]]; then
        echo "Error: Repository directory '${TEST_REPO_DIR}' not found"
        exit 1
    fi
    TEST_REPO_DIR=$(realpath "${TEST_REPO_DIR}")
fi >&2

# Setup test environment
export TEST_SRC_RPM
export TEST_REPO_DIR
export TEST_VERBOSE
export TEST_ENGINE
export TEST_IMAGE
export PACKAGE_NAME
export TEST_JOBS

temp_dir=$(mktemp -d)
trap 'rm -rf "${temp_dir}"' EXIT

log_heading "Testing ${PACKAGE_NAME}"
log_info "RPM file(s): ${#RPM_PATHS[@]}"
for rpm_file in "${RPM_PATHS[@]}"; do
    log_info "  - ${rpm_file}"
done
if [[ -n ${TEST_SRC_RPM} ]]; then
    log_info "Source RPM file: ${TEST_SRC_RPM}"
fi
if [[ -n ${TEST_REPO_DIR} ]]; then
    log_info "Repository directory: ${TEST_REPO_DIR}"
fi
log_info "Container engine: ${TEST_ENGINE}"
log_info "Container image: ${TEST_IMAGE}"
log_info "Verbose mode: ${TEST_VERBOSE}"
log_info "Parallel jobs: ${TEST_JOBS}"

# Load default tests
default_tests_file="${base_dir}/ci/default-tests/tests-rpm.yml"
if [[ ! -f ${default_tests_file} ]]; then
    echo "Error: Default tests file '${default_tests_file}' not found"
    exit 1
fi >&2

test_data=$(yaml_to_json < "${default_tests_file}")
test_data=$(jq --arg dir "${base_dir}/ci/default-tests" 'to_entries | map(.value.source_dir = $dir) | from_entries' <<< "${test_data}")

# Load package-specific tests if they exist
package_tests_file="${base_dir}/test/rpms/${PACKAGE_NAME}.yml"
if [[ -f ${package_tests_file} ]]; then
    log_info "Including package-specific tests from ${package_tests_file}"
    package_test_data=$(yaml_to_json < "${package_tests_file}")
    # Handle empty/null YAML files (files with only comments)
    if [[ ${package_test_data} != "null" && -n ${package_test_data} ]]; then
        # Only set source_dir for package tests that define their own command.
        # Tests that only add known_issues (no command) are extending default tests
        # and should inherit the default test's source_dir to preserve path resolution.
        package_test_data=$(jq --arg dir "${package_dir}" '
            to_entries | map(
                if .value.command then
                    .value.source_dir = $dir
                else
                    .
                end
            ) | from_entries
        ' <<< "${package_test_data}")
        # Merge tests (package-specific tests override default tests with same name)
        test_data=$(jq -s '.[0] * .[1]' <(echo "${test_data}") <(echo "${package_test_data}"))
    else
        log_info "Package-specific tests file is empty or contains no tests; skipping"
    fi
fi

# Separate binary RPM tests from source RPM tests
# Source RPM tests are those with names starting with "src-"
binary_rpm_test_names=$(jq -r 'keys_unsorted[] | select(startswith("src-") | not)' <<< "${test_data}")
src_rpm_test_names=$(jq -r 'keys_unsorted[] | select(startswith("src-"))' <<< "${test_data}")

# Function to run tests for a single RPM
# Arguments: rpm_file rpm_index total_rpms result_dir
# Outputs results to result_dir/results.txt and logs to result_dir/output.log
run_rpm_tests() {
    local rpm_file=$1
    local rpm_index=$2
    local total_rpms=$3
    local result_dir=$4
    local output_log="${result_dir}/output.log"
    local results_file="${result_dir}/results.txt"
    local rpm_basename
    rpm_basename=$(basename "${rpm_file}")

    export TEST_RPM="${rpm_file}"

    # Capture all output for this RPM
    {
        log_heading "Testing Binary RPM ${rpm_index}/${total_rpms}: ${rpm_basename}"

        # Run binary RPM tests
        local current_test=0
        local total_tests=0
        local passed_tests=0
        local failed_tests=0
        local known_issue_tests=0
        local unexpected_pass_tests=0
        local known_issues_found=()

        while IFS= read -r test_name; do
            [[ -z ${test_name} ]] && continue
            total_tests=$((total_tests + 1))
            current_test=$((current_test + 1))

            log_heading "Test ${current_test}: ${test_name}"

            local single_test_data
            single_test_data=$(jq --compact-output --arg test_name "${test_name}" '.[$test_name]' <<< "${test_data}")

            log_info "Running test..."
            local command known_issues source_dir
            command=$(jq -r '.command' <<< "${single_test_data}")
            known_issues=$(jq -c '.known_issues // []' <<< "${single_test_data}")
            source_dir=$(jq -r '.source_dir // "."' <<< "${single_test_data}")

            # Run test in subshell to avoid side effects
            (
                [[ ${TEST_VERBOSE} == true ]] && set -x
                # Change to the directory where the test is defined
                cd "${source_dir}"
                # Ensure TEST_RPM, TEST_SRC_RPM, TEST_ENGINE and TEST_IMAGE are available in subshell
                export TEST_RPM TEST_SRC_RPM TEST_ENGINE TEST_IMAGE
                eval "${command}"
            ) &> "${output_log}.${current_test}" &

            if ! wait -n; then
                local issue_result
                issue_result=$(check_known_issues "${known_issues}" "${output_log}.${current_test}")
                if [[ -n "${issue_result}" ]]; then
                    # Trim leading/trailing whitespace from the combined line
                    local issue_line issue_url
                    issue_line=$(tr '\n' ' ' <<< "${issue_result}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                    log_known_failure "${issue_line}"
                    known_issue_tests=$((known_issue_tests + 1))
                    issue_url=$(head -n1 <<< "${issue_result}")
                    # Only add to known_issues_found if not empty/null
                    if [[ -n ${issue_url} && ${issue_url} != "null" ]]; then
                        known_issues_found+=("${issue_url}")
                    fi
                else
                    echo "Command output:"
                    cat "${output_log}.${current_test}"
                    log_fail "Test failed with unknown issue"
                    failed_tests=$((failed_tests + 1))
                fi
            else
                if [[ ${TEST_VERBOSE} == true ]]; then
                    echo "Command output:"
                    cat "${output_log}.${current_test}"
                fi

                if [[ ${known_issues} != "[]" ]]; then
                    local always_fail_issues
                    always_fail_issues=$(jq -cr '.[] | select(.fails == "always" or (.fails | not)) | .issue + " " + .description' <<< "${known_issues}")
                    if [[ -n "${always_fail_issues}" ]]; then
                        log_unexpected_pass "${always_fail_issues}"
                        unexpected_pass_tests=$((unexpected_pass_tests + 1))
                    else
                        log_pass "Test passed"
                        passed_tests=$((passed_tests + 1))
                    fi
                else
                    log_pass "Test passed"
                    passed_tests=$((passed_tests + 1))
                fi
            fi
        done <<< "${binary_rpm_test_names}"

        # Print summary for this RPM
        if (( known_issue_tests > 0 )); then
            log_heading "Known Failures Found for $(basename "${rpm_file}")"
            echo "${known_issues_found[@]}" | tr ' ' '\n' | grep -v '^null$' | grep -v '^$' | sort -u | sed 's/^/- /' || true
        fi

        log_heading "Test Summary for $(basename "${rpm_file}")"
        log_info "Passed: ${passed_tests}/${total_tests}"
        log_info "Known Failures: ${known_issue_tests}/${total_tests}"
        log_info "Unknown Failures: ${failed_tests}/${total_tests}"
        log_info "Unexpected Passes: ${unexpected_pass_tests}/${total_tests}"

        echo ""

        # Write results to file for aggregation
        cat > "${results_file}" << RESULTS_EOF
total_tests=${total_tests}
passed_tests=${passed_tests}
failed_tests=${failed_tests}
known_issue_tests=${known_issue_tests}
unexpected_pass_tests=${unexpected_pass_tests}
known_issues_found=${known_issues_found[*]:-}
RESULTS_EOF
    } > "${result_dir}/console.log" 2>&1

    # Return exit code based on test results
    if (( failed_tests > 0 || unexpected_pass_tests > 0 )); then
        return 1
    fi
    return 0
}
export -f run_rpm_tests
export -f log_heading log_pass log_unexpected_pass log_known_failure log_fail log_info
export -f check_known_issues
export test_data binary_rpm_test_names
export RED GREEN YELLOW LIGHT_CYAN NC

# Initialize overall counters
overall_total_tests=0
overall_passed_tests=0
overall_failed_tests=0
overall_known_issue_tests=0
overall_unexpected_pass_tests=0
declare -a overall_known_issues_found

# Run tests for each RPM (with parallelism support)
declare -a rpm_pids=()
declare -a rpm_result_dirs=()
rpm_index=0
total_rpms=${#RPM_PATHS[@]}

for rpm_file in "${RPM_PATHS[@]}"; do
    rpm_index=$((rpm_index + 1))

    # Create result directory for this RPM
    result_dir="${temp_dir}/rpm-${rpm_index}"
    mkdir -p "${result_dir}"
    rpm_result_dirs+=("${result_dir}")

    # Show which RPM is being tested (useful for parallel execution progress)
    log_info "Starting test [${rpm_index}/${total_rpms}]: ${rpm_file}"

    # Run tests (in background if parallel jobs > 1)
    if (( TEST_JOBS > 1 )); then
        run_rpm_tests "${rpm_file}" "${rpm_index}" "${total_rpms}" "${result_dir}" &
        rpm_pids+=($!)

        # Wait if we've hit the job limit
        if (( ${#rpm_pids[@]} >= TEST_JOBS )); then
            # Wait for at least one job to complete
            wait -n || true
            # Remove completed PIDs from array
            new_pids=()
            for pid in "${rpm_pids[@]}"; do
                if kill -0 "${pid}" 2>/dev/null; then
                    new_pids+=("${pid}")
                fi
            done
            rpm_pids=("${new_pids[@]}")
        fi
    else
        # Sequential execution - run and display output immediately
        # shellcheck disable=SC2310  # Intentional: continue on test failure
        run_rpm_tests "${rpm_file}" "${rpm_index}" "${total_rpms}" "${result_dir}" || true
        cat "${result_dir}/console.log"
    fi
done

# Wait for all remaining parallel jobs to complete
if (( TEST_JOBS > 1 )); then
    for pid in "${rpm_pids[@]}"; do
        wait "${pid}" || true
    done

    # Display output from all RPMs in order
    for result_dir in "${rpm_result_dirs[@]}"; do
        if [[ -f "${result_dir}/console.log" ]]; then
            cat "${result_dir}/console.log"
        fi
    done
fi

# Aggregate results from all RPMs
for result_dir in "${rpm_result_dirs[@]}"; do
    if [[ -f "${result_dir}/results.txt" ]]; then
        # Source the results file to get variables
        # shellcheck source=/dev/null
        source "${result_dir}/results.txt"
        overall_total_tests=$((overall_total_tests + total_tests))
        overall_passed_tests=$((overall_passed_tests + passed_tests))
        overall_failed_tests=$((overall_failed_tests + failed_tests))
        overall_known_issue_tests=$((overall_known_issue_tests + known_issue_tests))
        overall_unexpected_pass_tests=$((overall_unexpected_pass_tests + unexpected_pass_tests))
        if [[ -n ${known_issues_found:-} ]]; then
            # shellcheck disable=SC2206
            overall_known_issues_found+=(${known_issues_found})
        fi
    fi
done

# Run source RPM tests once (if any exist and TEST_SRC_RPM is provided)
if [[ -n ${src_rpm_test_names} ]]; then
    log_heading "Running Source RPM Tests"
    if [[ -n ${TEST_SRC_RPM} ]]; then
        log_info "Source RPM: ${TEST_SRC_RPM}"
    fi

    # Use the first binary RPM's TEST_RPM for any tests that might reference it
    if (( ${#RPM_PATHS[@]} > 0 )); then
        export TEST_RPM="${RPM_PATHS[0]}"
    fi

    # Run source RPM tests
    current_test=0
    total_tests=0
    passed_tests=0
    failed_tests=0
    known_issue_tests=0
    unexpected_pass_tests=0
    declare -a known_issues_found

    while IFS= read -r test_name; do
        [[ -z ${test_name} ]] && continue
        total_tests=$((total_tests + 1))
        current_test=$((current_test + 1))

        log_heading "Source RPM Test ${current_test}: ${test_name}"

        single_test_data=$(jq --compact-output --arg test_name "${test_name}" '.[$test_name]' <<< "${test_data}")

        log_info "Running test..."
        command=$(jq -r '.command' <<< "${single_test_data}")
        known_issues=$(jq -c '.known_issues // []' <<< "${single_test_data}")
        source_dir=$(jq -r '.source_dir // "."' <<< "${single_test_data}")

        # Run test in subshell to avoid side effects
        (
            [[ ${TEST_VERBOSE} == true ]] && set -x
            # Change to the directory where the test is defined
            cd "${source_dir}"
            # Ensure TEST_RPM, TEST_SRC_RPM, TEST_ENGINE and TEST_IMAGE are available in subshell
            export TEST_RPM TEST_SRC_RPM TEST_ENGINE TEST_IMAGE
            eval "${command}"
        ) &> "${temp_dir}/output.log" &

        if ! wait -n; then
            issue_result=$(check_known_issues "${known_issues}" "${temp_dir}/output.log")
            if [[ -n "${issue_result}" ]]; then
                # Trim leading/trailing whitespace from the combined line
                issue_line=$(tr '\n' ' ' <<< "${issue_result}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                log_known_failure "${issue_line}"
                known_issue_tests=$((known_issue_tests + 1))
                issue_url=$(head -n1 <<< "${issue_result}")
                # Only add to known_issues_found if not empty/null
                if [[ -n ${issue_url} && ${issue_url} != "null" ]]; then
                    known_issues_found+=("${issue_url}")
                fi
            else
                echo "Command output:"
                cat "${temp_dir}/output.log"
                log_fail "Test failed with unknown issue"
                failed_tests=$((failed_tests + 1))
            fi
        else
            if [[ ${TEST_VERBOSE} == true ]]; then
                echo "Command output:"
                cat "${temp_dir}/output.log"
            fi

            if [[ ${known_issues} != "[]" ]]; then
                always_fail_issues=$(jq -cr '.[] | select(.fails == "always" or (.fails | not)) | .issue + " " + .description' <<< "${known_issues}")
                if [[ -n "${always_fail_issues}" ]]; then
                    log_unexpected_pass "${always_fail_issues}"
                    unexpected_pass_tests=$((unexpected_pass_tests + 1))
                else
                    log_pass "Test passed"
                    passed_tests=$((passed_tests + 1))
                fi
            else
                log_pass "Test passed"
                passed_tests=$((passed_tests + 1))
            fi
        fi
    done <<< "${src_rpm_test_names}"

    # Print summary for source RPM tests
    if (( known_issue_tests > 0 )); then
        log_heading "Known Failures Found for Source RPM Tests"
        echo "${known_issues_found[@]}" | tr ' ' '\n' | grep -v '^null$' | grep -v '^$' | sort -u | sed 's/^/- /' || true
    fi

    log_heading "Source RPM Test Summary"
    log_info "Passed: ${passed_tests}/${total_tests}"
    log_info "Known Failures: ${known_issue_tests}/${total_tests}"
    log_info "Unknown Failures: ${failed_tests}/${total_tests}"
    log_info "Unexpected Passes: ${unexpected_pass_tests}/${total_tests}"

    # Accumulate source RPM test results into overall results
    overall_total_tests=$((overall_total_tests + total_tests))
    overall_passed_tests=$((overall_passed_tests + passed_tests))
    overall_failed_tests=$((overall_failed_tests + failed_tests))
    overall_known_issue_tests=$((overall_known_issue_tests + known_issue_tests))
    overall_unexpected_pass_tests=$((overall_unexpected_pass_tests + unexpected_pass_tests))
    overall_known_issues_found+=("${known_issues_found[@]}")

    echo ""
fi

# Print overall summary if multiple RPMs were tested or source RPM tests were run
has_src_rpm_tests=false
[[ -n ${src_rpm_test_names} ]] && has_src_rpm_tests=true

if (( ${#RPM_PATHS[@]} > 1 )) || [[ ${has_src_rpm_tests} == true ]]; then
    if (( overall_known_issue_tests > 0 )); then
        log_heading "Overall Known Failures Found"
        echo "${overall_known_issues_found[@]}" | tr ' ' '\n' | grep -v '^null$' | grep -v '^$' | sort -u | sed 's/^/- /' || true
    fi

    summary_title="Overall Test Summary"
    if (( ${#RPM_PATHS[@]} > 1 )) && [[ ${has_src_rpm_tests} == true ]]; then
        summary_title="Overall Test Summary (${#RPM_PATHS[@]} Binary RPMs + Source RPM)"
    elif (( ${#RPM_PATHS[@]} > 1 )); then
        summary_title="Overall Test Summary (${#RPM_PATHS[@]} Binary RPMs)"
    elif [[ ${has_src_rpm_tests} == true ]]; then
        summary_title="Overall Test Summary (Binary + Source RPM)"
    fi

    log_heading "${summary_title}"
    log_info "Passed: ${overall_passed_tests}/${overall_total_tests}"
    log_info "Known Failures: ${overall_known_issue_tests}/${overall_total_tests}"
    log_info "Unknown Failures: ${overall_failed_tests}/${overall_total_tests}"
    log_info "Unexpected Passes: ${overall_unexpected_pass_tests}/${overall_total_tests}"

    # Use overall results for exit code
    passed_tests=${overall_passed_tests}
    failed_tests=${overall_failed_tests}
    known_issue_tests=${overall_known_issue_tests}
    unexpected_pass_tests=${overall_unexpected_pass_tests}
fi

# Determine exit code
if (( failed_tests > 0 )); then
    log_fail "${failed_tests} test(s) failed with new/unexpected issues"
    exit 1
elif (( unexpected_pass_tests > 0 )); then
    log_unexpected_pass "${unexpected_pass_tests} test(s) passed but expected to fail"
    exit 1
elif (( known_issue_tests > 0 )); then
    log_known_failure "${known_issue_tests} test(s) failed with known issues"
else
    log_pass "All tests passed successfully!"
fi
