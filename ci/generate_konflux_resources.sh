#!/bin/bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Default values
BRANCH="${BRANCH:-main}"
TENANT="${TENANT:-hummingbird-tenant}"
GIT_REPO="${GIT_REPO:-https://gitlab.com/redhat/hummingbird/rpms.git}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --tenant)
            TENANT="$2"
            shift 2
            ;;
        --git-repo)
            GIT_REPO="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --branch BRANCH                       Git branch (default: main)"
            echo "  --tenant TENANT                       Konflux tenant (default: hummingbird-tenant)"
            echo "  --git-repo URL                        Git repository URL"
            echo "  --help, -h                            Show this help message"
            exit 0
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

# shellcheck disable=SC2312
mapfile -d '' rpms < <(find ./rpms -maxdepth 1 -mindepth 1 -type d -print0 | LC_ALL=C sort -z)

APPLICATION_NAME="rpms-${BRANCH}"

temp_dir=$(mktemp -d)
trap 'rm -rf "${temp_dir}"' EXIT

temp_variables="${temp_dir}/variables.yml"
temp_rpm_variables="${temp_dir}/rpm-variables.yml"
temp_template="${temp_dir}/konflux-resources.with.macros"
template_dir="konflux-templates"
template="${template_dir}/konflux-resources.yml.j2"

echo "Building template variables..." >&2
cat > "${temp_variables}" << EOF
---
application_name: ${APPLICATION_NAME}
branch: ${BRANCH}
tenant: ${TENANT}
git_repo: ${GIT_REPO}
rpms: []
EOF
for path in "${rpms[@]}"; do
    name=$(basename "${path}")
    (
        echo "name: ${name}"
        # resource names must not contain underscores, but some package names do (like createrepo_c)
        # resource names must also be lowercase, but some package names have uppercase (like R-*)
        # resource names must not contain '+', but some package names do (like perl-Text-Tabs+Wrap)
        # resource names must not contain '.', but some package names do (like dotnet8.0)
        component_name="${name//_/-}"
        component_name="${component_name//+/-}"
        component_name="${component_name//./-}"
        echo "component_name: ${component_name,,}-${BRANCH}"
        echo "repository: ${name}"
        echo "tags: [latest]"
    ) > "${temp_rpm_variables}"
    properties_file="${path}/properties.yml"
    if [[ -f "${properties_file}" ]]; then
        yq -i ". * load(\"${properties_file}\")" "${temp_rpm_variables}"
    fi
    yq -i ".rpms += [load(\"${temp_rpm_variables}\")]" "${temp_variables}"
done

echo "Rendering Konflux resources..." >&2
cat "${template_dir}"/macros/*.yml.j2 "${template}" > "${temp_template}"
if ! jinja2 \
    --strict \
    --format=yaml \
    "${temp_template}" \
    "${temp_variables}"; then
    (
        echo "Failed Konflux resource rendering, input:"
        cat "${temp_template}"
        echo "Variables:"
        cat "${temp_variables}"
    ) >&2
    exit 1
fi
