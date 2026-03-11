#!/usr/bin/python3
"""Check that Konflux pipeline commit statuses exist before MR approval.

This script gates automated MR approval by verifying that Konflux
(Pipelines as Code) has posted commit statuses for the current commit,
i.e. that the pipelines have been invoked.

Pipelines that are still running are considered sufficient -- once
invoked, GitLab's merge_when_pipeline_succeeds handles waiting for
results.  The script only blocks approval when no Konflux statuses have
been posted yet (polls until they appear or a timeout is reached) or
when a pipeline has already failed.

Exit codes:
  0 - Konflux statuses found (running or successful)
  1 - Konflux statuses missing, timed out, or failed
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

# Konflux/PAC build pipeline commit statuses are prefixed with the cluster name.
# Example: "Konflux kflux-prd-rh03 / ruff-main-on-pull-request"
KONFLUX_NAME_PREFIX = "Konflux kflux-prd-rh03 /"

# Default polling configuration
DEFAULT_POLL_INTERVAL = 60  # seconds between API checks
DEFAULT_POLL_TIMEOUT = 120 * 60  # total seconds to wait (2 hours)


def get_commit_statuses(
    gitlab_url: str, project_id: str, commit_sha: str, token: str
) -> list[dict[str, object]]:
    """Fetch commit statuses from the GitLab API."""
    url = (
        f"{gitlab_url}/api/v4/projects/{project_id}"
        f"/repository/commits/{commit_sha}/statuses?per_page=100"
    )
    req = urllib.request.Request(url, headers={"PRIVATE-TOKEN": token})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())  # type: ignore[no-any-return]


def filter_konflux_statuses(
    statuses: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return only Konflux build pipeline statuses."""
    return [s for s in statuses if str(s.get("name", "")).startswith(KONFLUX_NAME_PREFIX)]


def check_statuses(konflux_statuses: list[dict[str, object]]) -> str:
    """Validate Konflux statuses and return a result string.

    Returns:
      "invoked"  - at least one status exists and none have failed
                   (includes running/pending/success)
      "missing"  - no Konflux statuses found at all
      "failed"   - at least one status has failed
    """
    if not konflux_statuses:
        return "missing"

    failed = [s for s in konflux_statuses if s.get("status") == "failed"]
    if failed:
        return "failed"

    return "invoked"


def print_statuses(konflux_statuses: list[dict[str, object]]) -> None:
    """Print Konflux pipeline statuses."""
    print(f"  Found {len(konflux_statuses)} Konflux pipeline status(es):")
    for s in konflux_statuses:
        print(f"    {s['name']}: {s['status']}")


def main(
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    poll_timeout: int = DEFAULT_POLL_TIMEOUT,
) -> int:
    """Poll for Konflux pipeline statuses and return 0 once invoked."""
    gitlab_url = os.environ.get("CI_SERVER_URL", "https://gitlab.com")
    project_id = os.environ["CI_PROJECT_ID"]
    token = os.environ["CHORE_MR_APPROVAL_GITLAB_TOKEN"]

    # PAC posts commit statuses to the source branch HEAD.
    # For merged-result pipelines, CI_COMMIT_SHA is the merge commit,
    # so prefer CI_MERGE_REQUEST_SOURCE_BRANCH_SHA when available.
    commit_sha = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA") or os.environ[
        "CI_COMMIT_SHA"
    ]

    print(f"Checking Konflux pipeline statuses for commit {commit_sha[:12]}...")

    deadline = time.monotonic() + poll_timeout

    while True:
        statuses = get_commit_statuses(gitlab_url, project_id, commit_sha, token)
        konflux_statuses = filter_konflux_statuses(statuses)
        result = check_statuses(konflux_statuses)

        if result == "invoked":
            print_statuses(konflux_statuses)
            print("\nKonflux pipelines have been invoked. Proceeding with approval.")
            return 0

        if result == "failed":
            print_statuses(konflux_statuses)
            failed = [s for s in konflux_statuses if s.get("status") == "failed"]
            print(f"\nERROR: {len(failed)} Konflux pipeline(s) failed:")
            for s in failed:
                print(f"  {s['name']}: {s['status']}")
            print("Skipping approval due to Konflux build failure(s).")
            return 1

        # result == "missing" -- poll until statuses appear or timeout
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            print("ERROR: Timed out waiting for Konflux pipeline statuses.")
            print("No Konflux statuses were ever posted for this commit.")
            all_names = [s.get("name") for s in statuses]
            if all_names:
                print(f"Commit statuses found: {all_names}")
            return 1

        print(
            f"  No Konflux statuses yet, retrying in {poll_interval}s"
            f" ({int(remaining)}s remaining)..."
        )
        time.sleep(poll_interval)


if __name__ == "__main__":
    sys.exit(main())
