#!/bin/bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Default values
BRANCH=${BRANCH:-main}
TENANT=${TENANT:-rhel-primitives-tenant}
RESOURCE_TYPE=""

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
            echo "  --tenant TENANT      Konflux tenant (default: rhel-primitives-tenant)"
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

PIPELINE_URL="https://github.com/scoheb/rpmbuild-pipeline.git"
PIPELINE_REVISION="add-pulp-support"
PIPELINE_PATH="pipeline/rhel-primitives-build-rpm-package.yaml"

# shellcheck disable=SC2312
mapfile -d '' rpms < <(find ./rpms -maxdepth 1 -mindepth 1 -type d -print0 | LC_ALL=C sort -z)

echo "Building template variables..." >&2
cat > "${temp_variables}" << EOF
---
branch: ${BRANCH}
application_name: ${APPLICATION_NAME}
pipeline_url: ${PIPELINE_URL}
pipeline_revision: ${PIPELINE_REVISION}
pipeline_path: ${PIPELINE_PATH}
tenant: ${TENANT}
rpms: []
EOF

for path in "${rpms[@]}"; do
    dname=$(basename "${path}")
    name=${dname}-${BRANCH}

    (
        echo "name: ${name}"
        echo "dname: ${dname}"
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
