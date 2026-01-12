#!/bin/bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Default values
BRANCH=${BRANCH:-main}
TENANT=${TENANT:-hummingbird-tenant}
RESOURCE_TYPE=""
# changes to ci/ also trigger the build pipeline for this rpm (as canary)
BUILD_TRIGGER_RPM_NAME=${BUILD_TRIGGER_RPM_NAME:-setup}

# Per-package configuration file for timeouts and build platforms
# See ci/package-overrides.yaml for overrides
PACKAGE_CONFIG="ci/package-overrides.yaml"
DEFAULT_TIMEOUT_HOURS=4


# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --branch)
            BRANCH=$2
            shift 2
            ;;
        --tenant)
            TENANT=$2
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 RESOURCE_TYPE [OPTIONS]"
            echo ""
            echo "RESOURCE_TYPE: 'push' or 'pull-request'"
            echo ""
            echo "Options:"
            echo "  --branch BRANCH      Git branch (default: main)"
            echo "  --tenant TENANT      Konflux tenant (default: hummingbird-tenant)"
            echo "  --help, -h           Show this help message"
            exit 0
            ;;
        push|pull-request)
            if [[ -n ${RESOURCE_TYPE} ]]; then
                echo "Error: Multiple resource types specified" >&2
                exit 1
            fi
            RESOURCE_TYPE=$1
            shift
            ;;
        -*)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
        *)
            echo "Unexpected argument: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

if [[ -z ${RESOURCE_TYPE} ]]; then
    echo "Usage: $0 push|pull-request [OPTIONS]" >&2
    exit 1
fi

temp_dir=$(mktemp -d)
trap 'rm -rf "${temp_dir}"' EXIT

temp_variables=${temp_dir}/variables.yml
temp_rpm_variables=${temp_dir}/rpm_variables.yml

template=.tekton/rpms-on-${RESOURCE_TYPE}.yaml.j2

APPLICATION_NAME="rpms-${BRANCH}"

# renovate: datasource=docker depName=quay.io/hummingbird-ci/rpmbuild-pipeline
PIPELINE_BUNDLE="quay.io/hummingbird-ci/rpmbuild-pipeline:latest@sha256:1976f39ea00eb5f8991c48c0ad182f908ac049c56d3a2e2ccda1142c8ae3c444"

# shellcheck disable=SC2312
mapfile -d '' rpms < <(find ./rpms -maxdepth 1 -mindepth 1 -type d -print0 | LC_ALL=C sort -z)

echo "Building template variables..." >&2
cat > "${temp_variables}" << EOF
---
branch: ${BRANCH}
application_name: ${APPLICATION_NAME}
pipeline_bundle: ${PIPELINE_BUNDLE}
tenant: ${TENANT}
rpms: []
EOF

for path in "${rpms[@]}"; do
    dname=$(basename "${path}")
    # resource names must not contain underscores, but some package names do (like createrepo_c)
    # resource names must also be lowercase, but some package names have uppercase (like R-*)
    # resource names must not contain '+', but some package names do (like perl-Text-Tabs+Wrap)
    component_name=${dname//_/-}
    component_name=${component_name//+/-}
    name=${component_name,,}-${BRANCH}

    (
        echo "name: ${name}"
        echo "dname: ${dname}"

        # Always include timeout_hours, using configured value or default
        if timeout_hours=$(yq -e ".${dname}.timeout_hours" "${PACKAGE_CONFIG}" 2>/dev/null); then
            echo "timeout_hours: ${timeout_hours}"
        else
            echo "timeout_hours: ${DEFAULT_TIMEOUT_HOURS}"
        fi

        # Only include build_platforms if overridden in the config file
        if build_platforms=$(yq -e ".${dname}.build_platforms[]" "${PACKAGE_CONFIG}" 2>/dev/null); then
            echo "build_platforms:"
            echo "${build_platforms}" | while read -r platform; do
                echo "  - ${platform}"
            done
        fi

        # Only include task_run_specs if overridden in the config file
        if yq -e ".${dname}.task_run_specs" "${PACKAGE_CONFIG}" &>/dev/null; then
            echo "task_run_specs:"
            yq ".${dname}.task_run_specs" "${PACKAGE_CONFIG}" | sed 's/^/  /'
        fi

        extra_paths=()

        # Add package-specific test file if it exists
        if [[ -f "test/rpms/${dname}.yml" ]]; then
            extra_paths+=("test/rpms/${dname}.yml")
        fi

        # Add ci/ and mock/ path changes for canary rpm
        if [[ ${dname} == "${BUILD_TRIGGER_RPM_NAME}" && ${RESOURCE_TYPE} == pull-request ]]; then
            extra_paths+=("ci/***")
            extra_paths+=("mock/***")
        fi

        if [[ ${#extra_paths[@]} -gt 0 ]]; then
            echo "extra_path_changes:"
            for path_change in "${extra_paths[@]}"; do
                echo "  - ${path_change}"
            done
        fi
    ) > "${temp_rpm_variables}"

    yq -i ".rpms += [load(\"${temp_rpm_variables}\")]" "${temp_variables}"
done

temp_template=${temp_dir}/pac-resources.with.macros

echo "Rendering Pipeline as Code resources..." >&2
cat .tekton/macros/*.j2 "${template}" > "${temp_template}"
if ! jinja2 \
    --strict \
    --format=yaml \
    "${temp_template}" \
    "${temp_variables}"; then
    (
        echo "Failed PAC resource rendering, input:"
        cat "${temp_template}"
        echo "Variables:"
        cat "${temp_variables}"
    ) >&2
    exit 1
fi
