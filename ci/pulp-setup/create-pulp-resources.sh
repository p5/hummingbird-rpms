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

# Optional third argument: path to pulp CLI config (e.g., ci.toml)
PULP_CONFIG_FILE=$3
PULP_CONFIG_OPT=()
if [[ -n "${PULP_CONFIG_FILE}" ]]; then
  PULP_CONFIG_OPT=(--config "${PULP_CONFIG_FILE}")
  echo "ℹ️ Using pulp config file: ${PULP_CONFIG_FILE}"
fi

# Parse comma-delimited string into array
IFS=',' read -ra PULP_REPOSITORIES <<< "${PULP_REPOSITORIES_STRING}"

# Remove leading/trailing whitespace from each repository name
for i in "${!PULP_REPOSITORIES[@]}"; do
  PULP_REPOSITORIES[i]=$(echo "${PULP_REPOSITORIES[i]}" | xargs)
done

echo "ℹ️ Will create repositories: ${PULP_REPOSITORIES[*]}"

# Check domain existence robustly (avoids pagination/truncation)
if pulp "${PULP_CONFIG_OPT[@]}" domain show --name "${PULP_DOMAIN}" >/dev/null 2>&1; then
  echo "ℹ️ Domain '${PULP_DOMAIN}' already exists. Skipping creation."
else
  echo "🆕 Domain '${PULP_DOMAIN}' not found. Creating..."
  # Attempt creation; if it already exists, report and continue
  if ! pulp "${PULP_CONFIG_OPT[@]}" console populated-domain create --name "${PULP_DOMAIN}" >/dev/null 2>&1; then
    echo "⚠️  Domain creation reported an error; verifying existence..."
    if ! pulp "${PULP_CONFIG_OPT[@]}" domain show --name "${PULP_DOMAIN}" >/dev/null 2>&1; then
      echo "🔴 Error: Failed to create domain '${PULP_DOMAIN}' and it does not exist."
      exit 1
    fi
    echo "ℹ️ Domain '${PULP_DOMAIN}' now exists. Continuing."
  fi
fi

# Create repositories
for PULP_REPOSITORY in "${PULP_REPOSITORIES[@]}"; do
    echo "🔄 Processing repository: ${PULP_REPOSITORY}"

    if pulp "${PULP_CONFIG_OPT[@]}" --domain "${PULP_DOMAIN}" rpm repository show --name "${PULP_REPOSITORY}" >/dev/null 2>&1; then
      echo "ℹ️ Repository '${PULP_REPOSITORY}' already exists. Skipping creation."
    else
      echo "🆕 Repository '${PULP_REPOSITORY}' not found. Creating..."
      pulp "${PULP_CONFIG_OPT[@]}" --domain "${PULP_DOMAIN}" rpm repository create --name "${PULP_REPOSITORY}"
      pulp "${PULP_CONFIG_OPT[@]}" --domain "${PULP_DOMAIN}" rpm repository update --name "${PULP_REPOSITORY}" --autopublish
    fi
    # Ensure distribution exists (recreate if it was deleted)
    if pulp "${PULP_CONFIG_OPT[@]}" --domain "${PULP_DOMAIN}" rpm distribution show --name "${PULP_REPOSITORY}" >/dev/null 2>&1; then
      echo "ℹ️ Distribution '${PULP_REPOSITORY}' already exists. Skipping creation."
    else
      echo "🆕 Distribution '${PULP_REPOSITORY}' not found. Creating..."
      pulp "${PULP_CONFIG_OPT[@]}" --domain "${PULP_DOMAIN}" rpm distribution create \
        --name "${PULP_REPOSITORY}" \
        --repository "${PULP_REPOSITORY}" \
        --base-path "${PULP_REPOSITORY}"
    fi
done
echo "✅ Setup complete."
