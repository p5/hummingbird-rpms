# Release Engineering Onboarding Script

This script automates the onboarding of components to release engineering
repositories, including pyxis-repo-configs and konflux-release-data.

## Overview

The script performs the following tasks:

1. Discovers components in the configured directory (e.g., `images/`, `rpms/`)
2. Creates/updates a YAML configuration file in pyxis-repo-configs
3. Creates merge requests with auto-merge enabled
4. Generates ReleasePlanAdmissions for konflux-release-data (optional)
5. Monitors and merges MRs when CI passes

## Features

- **Stateless operation**: No local tracking files needed; queries GitLab for current state
- **Idempotent**: Safe to run repeatedly; skips unchanged content
- **Auto-merge**: MRs are configured to merge automatically when CI passes
- **Dry-run mode**: Preview changes without making modifications

## Prerequisites

- Python 3.10+
- GitLab API token with write access to target repositories
- Required Python packages: `requests`, `pyyaml`, `jinja2`

## Authentication

Set the `GITLAB_TOKEN` environment variable with a GitLab API token that has
write access to the target repositories:

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
```

**Important**: Always use the environment variable instead of the `--gitlab-token`
CLI argument. CLI arguments can be visible in process listings and shell history,
which poses a security risk.

## Usage

### Basic Usage

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"

python3 ci/onboard_components_to_releng.py \
  --gitlab-url "https://gitlab.cee.redhat.com" \
  --pyxis-repo-configs-project-path "releng/pyxis-repo-configs" \
  --konflux-release-data-repo-path "org/konflux-release-data"
```

### Dry Run (preview changes)

```bash
python3 ci/onboard_components_to_releng.py --dry-run
```

### Check Only (check MR status without onboarding)

```bash
python3 ci/onboard_components_to_releng.py --check-only
```

### Debug Mode

```bash
python3 ci/onboard_components_to_releng.py --log-level DEBUG
```

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--gitlab-token` | GitLab API token (prefer `GITLAB_TOKEN` env var) | `GITLAB_TOKEN` env var |
| `--gitlab-url` | GitLab server URL | `https://gitlab.cee.redhat.com` |
| `--pyxis-repo-configs-project-path` | GitLab project path for pyxis-repo-configs | `releng/pyxis-repo-configs` |
| `--pyxis-file-path` | File path within pyxis-repo-configs | `products/hummingbird/hummingbird-tech-preview.yaml` |
| `--konflux-release-data-repo-path` | GitLab project path for konflux-release-data | None (RPA generation skipped if not set) |
| `--konflux-repo-url` | GitLab URL for konflux repo | Same as `--gitlab-url` |
| `--components-dir` | Path to components directory | Inferred from RPA config `component_filter.path_prefix`, or `images` |
| `--template` | Jinja2 template for pyxis YAML | `ci/templates/pyxis-repo-config.j2` |
| `--rpa-config-path` | RPA configuration file | `ci/konflux_rpa_config.yml` |
| `--rpa-template-dir` | Directory containing RPA templates | `konflux-templates` |
| `--dry-run` | Preview changes without making modifications | False |
| `--check-only` | Only check MR status, don't onboard | False |
| `--force` | Force regeneration even if unchanged | False |
| `--force-rpa` | Force RPA regeneration even when pyxis is up-to-date | False |
| `--skip-pyxis-mr` | Skip pyxis-repo-configs MR and only create release-data MR | False |
| `--wait-for-post-merge-pipeline` | Wait for pyxis post-merge pipeline before generating RPAs | True |
| `--no-wait-for-post-merge-pipeline` | Skip waiting for post-merge pipeline | - |
| `--post-merge-pipeline-timeout` | Timeout in seconds for post-merge pipeline wait | `600` (10 min) |
| `--wait-for-mr-pipeline` | Wait for MR CI pipeline after creating/updating an MR | True |
| `--no-wait-for-mr-pipeline` | Skip waiting for MR CI pipeline | - |
| `--mr-pipeline-timeout` | Timeout in seconds for MR CI pipeline wait | `3600` (1 hour) |
| `--preview-rpa` | Generate RPA files locally for verification and stop | None |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

## Configuration Files

### Pyxis Template (`ci/templates/pyxis-repo-config.j2`)

Jinja2 template for generating the pyxis-repo-configs YAML file. Receives a
`repositories` list containing repository configurations.

### RPA Configuration (`ci/konflux_rpa_config.yml`)

Defines ReleasePlanAdmission generation settings:

```yaml
global:
  branch: main
  tenant: hummingbird-tenant
  release_tenant: rhtap-releng-tenant

rpas:
  - name: hummingbird-containers-tech-preview-staging
    target_file: config/.../hummingbird-containers-tech-preview-staging.yaml
    template: macros/releng/release-plan-admission.yml.j2
    application_prefix: containers
    release_org: registry.stage.redhat.io/hummingbird-tech-preview
    single_component_mode: false
    service_account_name: release-registry-staging
    skip_pyxis_mr: false  # Set to true to skip pyxis MR for this RPA
    component_filter:
      path_prefix: images/  # Directory containing components (images/, rpms/, etc.)
```

**Note**: `skip_pyxis_mr` can be set at either level:
- **Per-RPA**: If ALL RPAs have `skip_pyxis_mr: true`, pyxis MR is skipped
- **Global**: Set `skip_pyxis_mr: true` in the `global` section to skip for all RPAs

The `component_filter.path_prefix` is also used to automatically infer the `--components-dir`
if not specified on the command line.

## GitLab CI Integration

The script is integrated into the CI pipeline via the `onboard_components_to_releng` job
in `.gitlab-ci.yml`. It runs:

- On scheduled pipelines (set `ONLY_JOB_NAME=onboard_components_to_releng`)
- Manually on merge requests

### Required CI/CD Variables

| Variable | Description |
|----------|-------------|
| `PYXIS_ONBOARDING_GITLAB_TOKEN` | Token with write access to target repos |
| `KONFLUX_RELEASE_DATA_REPO_PATH` | Path to konflux-release-data repo |

### Optional CI/CD Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYXIS_REPO_CONFIGS_PROJECT_PATH` | Pyxis repo path | `releng/pyxis-repo-configs` |
| `PYXIS_FILE_PATH` | File path in pyxis repo | `products/hummingbird/...` |
| `KONFLUX_REPO_URL` | Konflux GitLab URL | Same as CI server |
| `LOG_LEVEL` | Logging level | `INFO` |
| `PYXIS_ONBOARDING_DRY_RUN` | Enable dry-run | `false` |
| `PYXIS_ONBOARDING_CHECK_ONLY` | Check only mode | `false` |
| `PYXIS_ONBOARDING_FORCE` | Force regeneration | `false` |
| `PYXIS_ONBOARDING_FORCE_RPA` | Force RPA regeneration | `false` |
| `PYXIS_WAIT_FOR_POST_MERGE_PIPELINE` | Wait for post-merge pipeline | `true` |
| `PYXIS_POST_MERGE_PIPELINE_TIMEOUT` | Post-merge pipeline timeout (seconds) | `600` |

### Setting Up Scheduled Runs

1. Go to **Build → Pipeline schedules → New schedule**
2. Set cron expression (e.g., `0 */6 * * *` for every 6 hours)
3. Add variable: `ONLY_JOB_NAME` = `onboard_components_to_releng`
4. Save the schedule

## Forcing RPA Regeneration

If you've updated an RPA template and need to regenerate RPAs without any pyxis
changes, use `--force-rpa`:

```bash
python3 ci/onboard_components_to_releng.py \
  --konflux-release-data-repo-path "org/konflux-release-data" \
  --force-rpa
```

This is useful when:

- RPA templates have been updated and need to be re-applied
- A konflux MR CI failed due to template issues that have been fixed locally
- You need to update an existing konflux MR with regenerated content

The script will regenerate RPAs from the updated templates and push them to
the existing konflux MR branch (or create a new one if needed).

## Post-Merge Pipeline Waiting

By default, the script waits for the pyxis-repo-configs post-merge pipeline to
complete before generating RPAs. This ensures that any artifacts or state
produced by the pipeline are available for the konflux-release-data CI.

The script will:

1. Merge the pyxis-repo-configs MR
2. Wait for the post-merge pipeline to complete (up to 10 minutes by default)
3. Then generate and submit the konflux-release-data RPA MR

To customize the timeout:

```bash
python3 ci/onboard_components_to_releng.py \
  --konflux-release-data-repo-path "org/konflux-release-data" \
  --post-merge-pipeline-timeout 900
```

To disable waiting (not recommended if konflux CI depends on pyxis artifacts):

```bash
python3 ci/onboard_components_to_releng.py \
  --konflux-release-data-repo-path "org/konflux-release-data" \
  --no-wait-for-post-merge-pipeline
```

## MR Pipeline Waiting

By default, the script waits for MR CI pipelines to complete after creating or
updating merge requests. This ensures that approval and merge operations happen
only after CI validation.

The script will:

1. Create or update the MR
2. Wait for the CI pipeline to complete (up to 1 hour by default)
3. Attempt to approve and merge once CI passes

To customize the timeout:

```bash
python3 ci/onboard_components_to_releng.py \
  --mr-pipeline-timeout 1800  # 30 minutes
```

To disable waiting (MRs will be left for a subsequent run to merge):

```bash
python3 ci/onboard_components_to_releng.py --no-wait-for-mr-pipeline
```

## RPA Preview Mode

Use `--preview-rpa` to generate ReleasePlanAdmission files locally without
making any remote API calls. This is useful for verifying RPA content before
submitting to the konflux-release-data repository.

```bash
python3 ci/onboard_components_to_releng.py --preview-rpa
```

By default, files are written to `./rpa-preview/`. Specify a custom directory:

```bash
python3 ci/onboard_components_to_releng.py --preview-rpa /tmp/my-rpa-preview
```

Preview mode:

- Does not require a GitLab token
- Preserves the target directory structure from the RPA config
- Allows verification of template rendering before submission

After verifying the generated files, re-run without `--preview-rpa` to submit
the actual MR.

## Approval Workflow

When an MR's CI pipeline passes and approvals are pending, the script will
attempt to approve the MR via the GitLab API. This may succeed if:

- The token owner is an eligible approver
- Self-approval is allowed in the project settings
- The token has sufficient permissions

If API approval fails (e.g., due to self-approval restrictions), the script
will log a message suggesting manual approval in the GitLab UI.

The typical workflow is:

1. **Script creates/updates MR** → MR awaits CI and approval
2. **CI pipeline passes** → Script attempts API approval
3. **If API approval succeeds** → Script merges the MR
4. **If API approval fails** → Human approves in GitLab UI, script merges on next run

**Note**: Some GitLab configurations prevent the MR author from approving their
own MRs via the API, even if self-approval is allowed in the UI. In these cases,
manual approval in the GitLab UI is required.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. INITIALIZATION                                          │
│     Parse arguments, setup GitLab client                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. CHECK EXISTING MRs                                      │
│     Query GitLab for open MRs on hummingbird/onboard-images │
│     Attempt to merge if CI passed and approved              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. DISCOVER COMPONENTS                                     │
│     Scan components directory for properties.yml files      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. ONBOARD COMPONENTS                                      │
│     Fetch remote YAML, compute diff, create/update MR       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. GENERATE RPAs (if konflux configured)                   │
│     Extract metadata, render templates, create MR           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  6. CHECK KONFLUX MRs                                       │
│     Query for open hummingbird/update-rpa-* MRs             │
│     Merge if ready                                          │
└─────────────────────────────────────────────────────────────┘
```

## Branch Naming

The script uses the following branch naming conventions:

| Repository | Branch Pattern |
|------------|----------------|
| pyxis-repo-configs | `hummingbird/onboard-images` |
| konflux-release-data | `hummingbird/update-rpa-{pyxis_mr_id}` |

## Troubleshooting

### "File does not exist, creating initial structure"

The target file doesn't exist in the remote repository. The script will create
it with all discovered components.

### "No open MRs found"

No pending MRs exist. Either they were already merged or no changes were needed.
Use `--log-level DEBUG` to see merged/closed MR history.

### "MR has merge conflicts"

The target branch was updated directly. The script will attempt to rebase
automatically. If that fails, resolve conflicts manually in GitLab.

### "MR approval status: Pending (0/1 approvals)"

The script does not approve MRs automatically. A human must approve the MR in
the GitLab UI before it can be merged. See the [Approval Workflow](#approval-workflow)
section for details.

### "Auto-merge setting request sent, but GitLab API returned False"

This warning is expected when approval requirements are not yet met. GitLab
won't enable auto-merge until all merge requirements (approvals, CI) can be
satisfied. Once approved and CI passes, the MR will merge automatically or
on the next script run.

### "GitLab token lacks permission"

Ensure the `GITLAB_TOKEN` environment variable is set with a token that has
`api` scope and write access to both target repositories:

```bash
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
```
