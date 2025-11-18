#!/bin/bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Default values
BRANCH="${BRANCH:-main}"
TENANT="${TENANT:-hummingbird-tenant}"
GIT_REPO="${GIT_REPO:-https://gitlab.com/redhat/hummingbird/rpms.git}"

SKIP_KONFLUX=false
SKIP_PAC=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-konflux)
            SKIP_KONFLUX=true
            shift
            ;;
        --skip-pac)
            SKIP_PAC=true
            shift
            ;;
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
            echo "  --skip-konflux                        Skip Konflux resource generation"
            echo "  --skip-pac                            Skip Pipeline as Code generation"
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

rpms_on_push_yaml='.tekton/rpms-on-push.yaml'
rpms_on_pull_request_yaml='.tekton/rpms-on-pull-request.yaml'

if [[ "${SKIP_PAC}" == "true" ]]; then
    echo 'WARN: Skipping Pipeline as Code generation.'
else
    ./ci/generate_pac_resources.sh push \
        --branch "${BRANCH}" \
        --tenant "${TENANT}" \
        > "${rpms_on_push_yaml}"

    ./ci/generate_pac_resources.sh pull-request \
        --branch "${BRANCH}" \
        --tenant "${TENANT}" \
        > "${rpms_on_pull_request_yaml}"
fi

if [[ "${SKIP_KONFLUX}" == "true" ]]; then
    echo 'WARN: Skipping Konflux resource generation.'
else
    ./ci/generate_konflux_resources.sh \
        --branch "${BRANCH}" \
        --tenant "${TENANT}" \
        --git-repo "${GIT_REPO}" \
        > "konflux-templates/rendered.yml"
fi
