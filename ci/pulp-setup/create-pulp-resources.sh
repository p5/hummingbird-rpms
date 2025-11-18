#!/bin/bash

set -e

PULP_DOMAIN=$1

if [[ -z "${PULP_DOMAIN}" ]]; then
  echo "🔴 error: missing parameter PULP_DOMAIN"
  exit 1
fi

PULP_REPOSITORIES_STRING=$2
if [[ -z "${PULP_REPOSITORIES_STRING}" ]]; then
  echo "🔴 error: missing parameter PULP_REPOSITORIES (provide comma-delimited repository names)"
  exit 1
fi

# Parse comma-delimited string into array
IFS=',' read -ra PULP_REPOSITORIES <<< "${PULP_REPOSITORIES_STRING}"

# Remove leading/trailing whitespace from each repository name
for i in "${!PULP_REPOSITORIES[@]}"; do
  PULP_REPOSITORIES[i]=$(echo "${PULP_REPOSITORIES[i]}" | xargs)
done

echo "ℹ️ Will create repositories: ${PULP_REPOSITORIES[*]}"

pulp_domain_output=$(pulp domain list --field name)
DOMAIN_EXISTS=$(jq -r ".[] | select(.name == \"${PULP_DOMAIN}\") | .name" <<< "${pulp_domain_output}")
if [[ "${DOMAIN_EXISTS}" == "${PULP_DOMAIN}" ]]; then
    echo "ℹ️ Domain '${PULP_DOMAIN}' already exists. Skipping creation."
else
    echo "🆕 Domain '${PULP_DOMAIN}' not found. Creating..."
    pulp console populated-domain create --name "${PULP_DOMAIN}"
fi

# Create repositories
for PULP_REPOSITORY in "${PULP_REPOSITORIES[@]}"; do
    echo "🔄 Processing repository: ${PULP_REPOSITORY}"

    pulp_repo_output=$(pulp --domain "${PULP_DOMAIN}" rpm repository list --field name)
    REPO_EXISTS=$(jq -r ".[] | select(.name == \"${PULP_REPOSITORY}\") | .name" <<< "${pulp_repo_output}")

    if [[ "${REPO_EXISTS}" == "${PULP_REPOSITORY}" ]]; then
        echo "ℹ️ Repository '${PULP_REPOSITORY}' already exists. Skipping creation."
    else
        echo "🆕 Repository '${PULP_REPOSITORY}' not found. Creating..."
        pulp --domain "${PULP_DOMAIN}" rpm repository create --name "${PULP_REPOSITORY}"
        pulp --domain "${PULP_DOMAIN}" rpm repository update --name "${PULP_REPOSITORY}" --autopublish
        pulp --domain "${PULP_DOMAIN}" rpm distribution create --name "${PULP_REPOSITORY}" \
          --repository "${PULP_REPOSITORY}" --base-path "${PULP_REPOSITORY}"
    fi
done
echo "✅ Setup complete."
