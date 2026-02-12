#!/usr/bin/env python3
"""Onboard container image components to release engineering repositories.

This script:
1. Discovers images in the images/ directory that need onboarding
2. Updates products/hummingbird/hummingbird-tech-preview.yaml in pyxis-repo-configs
3. Generates ReleasePlanAdmissions in konflux-release-data
4. Creates merge requests with auto-merge enabled
5. Monitors MR status and merges when CI passes

Use --skip-pyxis-mr to skip pyxis-repo-configs and only create release-data MRs.
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
import yaml
import jinja2

# Logger will be configured in main() after parsing arguments
logger = logging.getLogger(__name__)

# Constants
PYXIS_REPO_URL = "https://gitlab.cee.redhat.com/releng/pyxis-repo-configs"
PYXIS_REPO_PATH = "products/hummingbird/hummingbird-tech-preview.yaml"
TEAM_ID = "693c25013d241b4327b92d4a"  # From the example YAML
PYXIS_BRANCH_NAME = "hummingbird/onboard-images"
KONFLUX_BRANCH_PREFIX = "hummingbird/update-rpa-"


class GitLabClient:
    """Client for interacting with GitLab API."""

    def __init__(self, base_url: str, token: str):
        """Initialize GitLab client."""
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v4"
        self.token = token
        self.headers = {
            "PRIVATE-TOKEN": token,
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a GitLab API request."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        response = requests.request(
            method,
            url,
            headers=self.headers,
            timeout=30,
            **kwargs,
        )
        if not response.ok:
            # Log error response body for debugging
            try:
                error_body = response.text
                logger.debug(f"GitLab API error response: {error_body}")
            except Exception:
                pass
        response.raise_for_status()
        return response

    def get_project_id(self, project_path: str) -> int:
        """Get project ID from project path."""
        encoded_path = project_path.replace("/", "%2F")
        response = self._request("GET", f"projects/{encoded_path}")
        return response.json()["id"]

    def create_branch(
        self,
        project_id: int,
        branch_name: str,
        ref: str = "main",
    ) -> None:
        """Create a new branch."""
        self._request(
            "POST",
            f"projects/{project_id}/repository/branches",
            json={"branch": branch_name, "ref": ref},
        )

    def delete_branch(
        self,
        project_id: int,
        branch_name: str,
    ) -> None:
        """Delete a branch."""
        encoded_branch = branch_name.replace("/", "%2F")
        self._request(
            "DELETE",
            f"projects/{project_id}/repository/branches/{encoded_branch}",
        )

    def get_file_content(
        self,
        project_id: int,
        file_path: str,
        ref: str = "main",
    ) -> str:
        """Get file content from repository."""
        encoded_path = file_path.replace("/", "%2F")
        response = self._request(
            "GET",
            f"projects/{project_id}/repository/files/{encoded_path}",
            params={"ref": ref},
        )
        import base64

        return base64.b64decode(response.json()["content"]).decode("utf-8")

    def create_or_update_file(
        self,
        project_id: int,
        file_path: str,
        content: str,
        branch: str,
        commit_message: str,
    ) -> None:
        """Create or update a file in the repository."""
        encoded_path = file_path.replace("/", "%2F")
        # Get existing file to get the blob_id if it exists
        try:
            existing = self._request(
                "GET",
                f"projects/{project_id}/repository/files/{encoded_path}",
                params={"ref": branch},
            )
            blob_id = existing.json()["blob_id"]
        except requests.HTTPError:
            blob_id = None

        import base64

        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        data = {
            "branch": branch,
            "commit_message": commit_message,
            "content": content_b64,
            "encoding": "base64",
        }
        if blob_id:
            data["last_commit_id"] = existing.json()["last_commit_id"]

        self._request(
            "POST" if blob_id is None else "PUT",
            f"projects/{project_id}/repository/files/{encoded_path}",
            json=data,
        )

    def create_merge_request(
        self,
        project_id: int,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
        merge_when_pipeline_succeeds: bool = False,
    ) -> dict[str, Any]:
        """Create a merge request.

        Args:
            merge_when_pipeline_succeeds: If True, automatically merge when pipeline succeeds.
        """
        json_data = {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "remove_source_branch": True,
        }
        if merge_when_pipeline_succeeds:
            # Try newer API parameter (GitLab 17.11+)
            # Only send one parameter to avoid 400 errors
            json_data["auto_merge"] = True

        response = self._request(
            "POST",
            f"projects/{project_id}/merge_requests",
            json=json_data,
        )
        return response.json()

    def update_merge_request(
        self,
        project_id: int,
        mr_iid: int,
        title: str | None = None,
        description: str | None = None,
        merge_when_pipeline_succeeds: bool | None = None,
    ) -> dict[str, Any]:
        """Update a merge request.

        Args:
            merge_when_pipeline_succeeds: If True, automatically merge when pipeline succeeds.
                                          If None, this setting is not changed.
        """
        json_data: dict[str, Any] = {}
        if title is not None:
            json_data["title"] = title
        if description is not None:
            json_data["description"] = description

        # Handle auto-merge separately using POST endpoint if needed
        auto_merge_enabled = None
        if merge_when_pipeline_succeeds is not None:
            auto_merge_enabled = merge_when_pipeline_succeeds

        if not json_data and auto_merge_enabled is None:
            # Nothing to update, just return the current MR
            return self.get_merge_request(project_id, mr_iid)

        # First, update title/description if needed
        if json_data:
            logger.debug(f"Updating MR {mr_iid} with data: {json_data}")
            response = self._request(
                "PUT",
                f"projects/{project_id}/merge_requests/{mr_iid}",
                json=json_data,
            )
            result = response.json()
        else:
            result = self.get_merge_request(project_id, mr_iid)

        # Then, handle auto-merge
        # GitLab may ignore merge_when_pipeline_succeeds if requirements aren't met,
        # but we still want to set it so it will auto-merge when requirements are satisfied
        if auto_merge_enabled is not None:
            try:
                if auto_merge_enabled:
                    # Try POST endpoint first (some GitLab versions use this)
                    logger.debug(f"Enabling auto-merge for MR {mr_iid}")
                    try:
                        response = self._request(
                            "POST",
                            f"projects/{project_id}/merge_requests/{mr_iid}/merge_when_pipeline_succeeds",
                        )
                        result = response.json()
                        logger.debug(f"MR {mr_iid} auto-merge enabled via POST endpoint")
                    except Exception as e:
                        # POST endpoint doesn't exist, use PUT with merge_when_pipeline_succeeds
                        logger.debug(f"POST endpoint not available, using PUT: {e}")
                        current_mr = result if "merge_when_pipeline_succeeds" in result else self.get_merge_request(project_id, mr_iid)
                        put_data = {
                            "title": current_mr.get("title", ""),
                            "merge_when_pipeline_succeeds": True,
                        }
                        response = self._request(
                            "PUT",
                            f"projects/{project_id}/merge_requests/{mr_iid}",
                            json=put_data,
                        )
                        updated_result = response.json()
                        logger.debug(f"MR {mr_iid} PUT response: merge_when_pipeline_succeeds={updated_result.get('merge_when_pipeline_succeeds')}")
                        result = updated_result

                        # GitLab may return False in the immediate response even if the setting is applied
                        # Fetch the MR again to verify if it was actually set
                        import time
                        time.sleep(0.5)  # Brief delay to allow GitLab to process
                        verify_mr = self.get_merge_request(project_id, mr_iid)
                        verify_merge_when = verify_mr.get("merge_when_pipeline_succeeds")
                        logger.debug(f"MR {mr_iid} verification fetch: merge_when_pipeline_succeeds={verify_merge_when}")

                        if verify_merge_when:
                            logger.info(f"✓ Auto-merge confirmed as enabled for MR {mr_iid}")
                        else:
                            # Still False - This is a known GitLab API limitation
                            # The API may ignore merge_when_pipeline_succeeds even though the UI allows setting it
                            # See: https://gitlab.com/gitlab-org/gitlab/-/issues/351111
                            logger.warning(
                                f"⚠ Auto-merge setting request sent for MR {mr_iid}, but GitLab API returned False. "
                                f"This is a known GitLab API limitation - the API may ignore this parameter even though "
                                f"the UI allows it. Please verify in the GitLab UI or manually enable auto-merge if needed. "
                                f"The setting may also activate automatically once all merge requirements (approvals, etc.) are met."
                            )
                else:
                    # To disable, use PUT
                    current_mr = result if "merge_when_pipeline_succeeds" in result else self.get_merge_request(project_id, mr_iid)
                    put_data = {
                        "title": current_mr.get("title", ""),
                        "merge_when_pipeline_succeeds": False,
                    }
                    response = self._request(
                        "PUT",
                        f"projects/{project_id}/merge_requests/{mr_iid}",
                        json=put_data,
                    )
                    result = response.json()
            except Exception as e:
                logger.warning(f"Could not set auto-merge for MR {mr_iid}: {e}")

        return result

    def get_merge_request(
        self,
        project_id: int,
        mr_iid: int,
    ) -> dict[str, Any]:
        """Get merge request details."""
        response = self._request(
            "GET",
            f"projects/{project_id}/merge_requests/{mr_iid}",
        )
        return response.json()

    def merge_merge_request(
        self,
        project_id: int,
        mr_iid: int,
        merge_commit_message: str | None = None,
        squash: bool | None = None,
        should_remove_source_branch: bool | None = None,
        merge_when_pipeline_succeeds: bool | None = None,
    ) -> dict[str, Any]:
        """Merge a merge request.

        Args:
            merge_commit_message: Custom merge commit message.
            squash: If True, squash commits into a single commit.
            should_remove_source_branch: If True, remove source branch after merge.
            merge_when_pipeline_succeeds: If True, merge when pipeline succeeds (for auto-merge).
        """
        json_data: dict[str, Any] = {}
        if merge_commit_message is not None:
            json_data["merge_commit_message"] = merge_commit_message
        if squash is not None:
            json_data["squash"] = squash
        if should_remove_source_branch is not None:
            json_data["should_remove_source_branch"] = should_remove_source_branch
        if merge_when_pipeline_succeeds is not None:
            json_data["merge_when_pipeline_succeeds"] = merge_when_pipeline_succeeds

        logger.debug(f"Merging MR {mr_iid} with data: {json_data}")
        response = self._request(
            "PUT",
            f"projects/{project_id}/merge_requests/{mr_iid}/merge",
            json=json_data if json_data else None,
        )
        result = response.json()
        logger.debug(f"MR {mr_iid} merge response: state={result.get('state')}, merged_at={result.get('merged_at')}")
        return result

    def rebase_merge_request(
        self,
        project_id: int,
        mr_iid: int,
    ) -> dict[str, Any]:
        """Rebase a merge request branch onto its target branch."""
        response = self._request(
            "PUT",
            f"projects/{project_id}/merge_requests/{mr_iid}/rebase",
        )
        return response.json()

    def list_merge_requests(
        self,
        project_id: int,
        state: str = "opened",
        source_branch: str | None = None,
    ) -> list[dict[str, Any]]:
        """List merge requests."""
        params = {"state": state}
        if source_branch:
            params["source_branch"] = source_branch
        response = self._request(
            "GET",
            f"projects/{project_id}/merge_requests",
            params=params,
        )
        return response.json()

    def get_merge_request_pipelines(
        self,
        project_id: int,
        mr_iid: int,
    ) -> list[dict[str, Any]]:
        """Get pipelines for a merge request."""
        try:
            response = self._request(
                "GET",
                f"projects/{project_id}/merge_requests/{mr_iid}/pipelines",
            )
            return response.json()
        except requests.HTTPError as e:
            # If pipelines endpoint doesn't exist or returns 404, return empty list
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                return []
            raise

    def get_branch_pipelines(
        self,
        project_id: int,
        branch: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get pipelines for a specific branch.

        Args:
            project_id: GitLab project ID
            branch: Branch name
            limit: Maximum number of pipelines to return (default: 5)
        """
        try:
            response = self._request(
                "GET",
                f"projects/{project_id}/pipelines",
                params={"ref": branch, "per_page": limit},
            )
            return response.json()
        except requests.HTTPError as e:
            # If pipelines endpoint doesn't exist or returns 404, return empty list
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                return []
            raise

    def get_merge_request_approvals(
        self,
        project_id: int,
        mr_iid: int,
    ) -> dict[str, Any]:
        """Get approval status for a merge request."""
        try:
            response = self._request(
                "GET",
                f"projects/{project_id}/merge_requests/{mr_iid}/approvals",
            )
            return response.json()
        except requests.HTTPError as e:
            # If approvals endpoint doesn't exist or returns 404, return empty dict
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                return {}
            raise

    def approve_merge_request(
        self,
        project_id: int,
        mr_iid: int,
    ) -> dict[str, Any]:
        """Approve a merge request.

        Note: This may fail if:
        - The user is the MR author and self-approval is not allowed
        - The user has already approved
        - The user doesn't have permission to approve

        Returns:
            Approval response dict on success, empty dict on failure
        """
        try:
            response = self._request(
                "POST",
                f"projects/{project_id}/merge_requests/{mr_iid}/approve",
            )
            return response.json()
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                try:
                    error_body = e.response.json()
                    error_msg = error_body.get("message", str(error_body))
                except Exception:
                    error_msg = e.response.text
                logger.debug(f"Approve MR {mr_iid} failed (HTTP {status_code}): {error_msg}")
                # Return empty dict instead of raising - approval failure is not fatal
                return {}
            raise


def get_repository_name(image_dir: Path) -> str:
    """Get repository name from properties.yml or use directory name."""
    properties_file = image_dir / "properties.yml"
    if properties_file.exists():
        properties = yaml.safe_load(properties_file.read_text(encoding="utf-8"))
        if repository := properties.get("repository"):
            return repository
    return image_dir.name


def discover_components(components_dir: Path) -> list[dict[str, Any]]:
    """Discover all components in the components directory.

    Components are detected by the presence of either:
    - properties.yml (for container images)
    - Any .spec file (for RPMs)
    """
    components = []
    for component_dir in sorted(components_dir.iterdir()):
        if not component_dir.is_dir():
            continue

        # Check for properties.yml (images) or .spec files (RPMs)
        properties_file = component_dir / "properties.yml"
        spec_files = list(component_dir.glob("*.spec"))

        if not properties_file.exists() and not spec_files:
            continue

        repository_name = get_repository_name(component_dir)
        components.append(
            {
                "name": component_dir.name,
                "repository": repository_name,
                "directory": component_dir,
            },
        )
    return components


def sanitize_component_name(name: str) -> str:
    """Sanitize package name for use as Kubernetes resource name."""
    # resource names must not contain underscores, uppercase, +, or .
    result = name.replace("_", "-").replace("+", "-").replace(".", "-")
    return result.lower()


def create_initial_yaml_structure(template_path: Path) -> str:
    """Create the initial YAML file structure with no repositories using the template."""
    return render_yaml_from_template(template_path, repositories=[])


def create_repository_entry(image_name: str, repository_name: str, use_merge_keys: bool = True) -> dict[str, Any]:
    """Create a repository entry for the YAML file.

    Uses YAML merge keys to reduce duplication by referencing common defaults.
    When use_merge_keys is True, the entry will use <<: *repo-defaults to reference
    the common defaults anchor.
    """
    # Common repository defaults (will be in anchor)
    repo_defaults = {
        "release_categories": ["Tech Preview"],
        "includes_multiple_content_streams": False,
        "content_stream_tags": ["latest"],
        "build_categories": ["Standalone image"],
        "team_id": TEAM_ID,
        "vendor_label": "redhat",
        "use_latest": True,
        "requires_terms": False,
        "privileged_images_allowed": False,
        "protected_for_pull": False,
        "protected_for_search": True,
        "publish_on_push": False,
        "catalog_visibility": "hidden",
        "contacts": "*team-contacts",
        "application_categories": ["Other"],
        "documentation_links": [
            {
                "title": "Project Hummingbird Tech Preview",
                "type": "Documentation",
                "url": "https://hummingbird-project.io/",
            },
        ],
    }

    if use_merge_keys:
        # Use merge key syntax - will be handled specially during YAML serialization
        repository_dict = {
            "<<": "*repo-defaults",  # Special marker for merge key
            "repository": f"hummingbird-tech-preview/{repository_name}",
            "display_data": {
                "name": f"Project Hummingbird Tech Preview {image_name} image",
                "long_description": f"Project Hummingbird Tech Preview {image_name} image",
            },
        }
    else:
        # Expand defaults (for PyYAML compatibility)
        repository_dict = {
            **repo_defaults,  # type: ignore[dict-item]
            "repository": f"hummingbird-tech-preview/{repository_name}",
            "display_data": {
                "name": f"Project Hummingbird Tech Preview {image_name} image",
                "long_description": f"Project Hummingbird Tech Preview {image_name} image",
            },
        }

    return {
        "image_type": "Base",  # Hummingbird
        "base_rhel_version": "rhel9",
        "repository": repository_dict,
    }


def render_yaml_from_template(
    template_path: Path,
    repositories: list[dict[str, Any]],
) -> str:
    """Render YAML from a Jinja2 template.

    Args:
        template_path: Path to the Jinja2 template file
        repositories: List of repository entries to include

    Returns:
        Rendered YAML content as string

    Note:
        The template should define all default data (team contacts, repository defaults)
        directly in the template. Only repositories are passed as context.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Load template
    template_content = template_path.read_text(encoding="utf-8")

    # Prepare template context - only pass repositories
    # Default data (team contacts, repository defaults) should be defined in the template
    context = {
        "repositories": repositories,
    }

    # Render template
    try:
        template = jinja2.Template(template_content, undefined=jinja2.StrictUndefined)
        rendered = template.render(**context)
        # Ensure output ends with a newline (yamllint requirement)
        if not rendered.endswith('\n'):
            rendered += '\n'
        return rendered
    except jinja2.UndefinedError as e:
        raise ValueError(f"Template rendering error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to render template: {e}") from e


def update_yaml_file(
    yaml_content: str,
    images_to_add: list[dict[str, str]],
    template_path: Path,
    valid_repository_names: set[str] | None = None,
) -> tuple[str, list[dict[str, str]], list[dict[str, str]], list[dict[str, Any]], list[dict[str, str]]]:
    """Update YAML file with new repository entries and remove entries for deleted images.

    Args:
        yaml_content: Current YAML file content
        images_to_add: List of dicts with 'name' and 'repository' keys
        valid_repository_names: Set of repository names that should exist locally.
                               Entries for hummingbird-tech-preview/* not in this set will be removed.

    Returns:
        Tuple of (updated_yaml_content, list_of_added_images, list_of_removed_images, list_of_updated_display_data, list_of_skipped_images)
    """
    # Parse YAML
    # The template always includes anchor definitions, so we can parse directly
    if yaml_content and yaml_content.strip():
        # Try to parse with ruamel.yaml if available (it supports merge keys)
        try:
            from ruamel.yaml import YAML  # type: ignore[import-not-found]

            yaml_obj = YAML()
            yaml_obj.allow_duplicate_keys = True
            try:
                data = yaml_obj.load(yaml_content)
                if data is None:
                    data = {}
            except Exception as ruamel_error:
                # If ruamel.yaml fails, try expanding merge keys first
                logger.debug(f"ruamel.yaml load failed, trying to expand merge keys: {ruamel_error}")
                try:
                    expanded_yaml = expand_merge_keys_from_yaml(yaml_content, template_path)
                    data = yaml.safe_load(expanded_yaml)
                except Exception as expand_error:
                    # If expansion also fails, try parsing directly (might be old format)
                    logger.debug(f"Failed to expand merge keys, trying direct parse: {expand_error}")
                    try:
                        data = yaml.safe_load(yaml_content)
                    except Exception as parse_error:
                        # If direct parse also fails, log and create initial structure
                        logger.warning(f"Failed to parse YAML content: {parse_error}, creating initial structure")
                        data = yaml.safe_load(create_initial_yaml_structure(template_path))
        except ImportError:
            # ruamel.yaml not available, use PyYAML with merge key expansion
            try:
                expanded_yaml = expand_merge_keys_from_yaml(yaml_content, template_path)
                data = yaml.safe_load(expanded_yaml)
            except Exception as e:
                # If expansion fails, try parsing directly (might be old format without merge keys)
                logger.debug(f"Failed to expand merge keys, trying direct parse: {e}")
                try:
                    data = yaml.safe_load(yaml_content)
                except Exception as parse_error:
                    # If direct parse also fails, log and create initial structure
                    logger.warning(f"Failed to parse YAML content: {parse_error}, creating initial structure")
                    data = yaml.safe_load(create_initial_yaml_structure(template_path))
    else:
        # If content is empty, create initial structure
        data = yaml.safe_load(create_initial_yaml_structure(template_path))

    if data is None:
        # If parsing resulted in None, create initial structure
        data = yaml.safe_load(create_initial_yaml_structure(template_path))

    # Ensure data is a dict before proceeding
    if not isinstance(data, dict):
        data = yaml.safe_load(create_initial_yaml_structure(template_path))

    # Ensure repositories list exists
    if "repositories" not in data:
        data["repositories"] = []
    elif data["repositories"] is None:
        data["repositories"] = []

    # Ensure repository-defaults anchor exists (for deduplication)
    # This anchor contains common repository settings to reduce duplication
    if "repository-defaults" not in data:
        # Add the defaults anchor if it doesn't exist
        defaults_data = yaml.safe_load(create_initial_yaml_structure(template_path))
        if "repository-defaults" in defaults_data:
            data["repository-defaults"] = defaults_data["repository-defaults"]

    # Expand any existing merge keys in the data (for compatibility)
    # This ensures we can work with both old (expanded) and new (with merge keys) formats
    data = _expand_existing_merge_keys(data)

    repositories = data.get("repositories", [])
    if repositories is None:
        repositories = []
    added_images = []
    removed_images = []
    skipped_images = []
    updated_display_data = []  # Track repositories whose display_data was updated

    # Build set of valid repository paths if provided
    valid_repo_paths = None
    if valid_repository_names is not None:
        valid_repo_paths = {f"hummingbird-tech-preview/{repo}" for repo in valid_repository_names}

    # First, remove entries for images that no longer exist locally
    if valid_repo_paths is not None:
        repositories_to_keep = []
        for repo in repositories:
            repo_path = repo.get("repository", {}).get("repository", "")
            # Only remove hummingbird-tech-preview entries that are not in valid set
            if repo_path.startswith("hummingbird-tech-preview/") and repo_path not in valid_repo_paths:
                # Extract image name from the repository entry
                repo_name = repo_path.replace("hummingbird-tech-preview/", "")
                # Try to find the image name from display_data
                display_name = repo.get("repository", {}).get("display_data", {}).get("name", "")
                # Extract image name from display name (format: "Project Hummingbird Tech Preview {name} image")
                image_name = display_name.replace("Project Hummingbird Tech Preview ", "").replace(" image", "")
                if not image_name:
                    image_name = repo_name
                removed_images.append({"name": image_name, "repository": repo_name})
                logger.info(f"Removed {image_name} ({repo_name}) from YAML (no longer exists locally)")
            else:
                repositories_to_keep.append(repo)
        repositories = repositories_to_keep

    # Add all new images that don't already exist
    logger.info(f"Checking {len(images_to_add)} image(s) for addition to YAML file")
    for image_info in images_to_add:
        image_name = image_info["name"]
        repository_name = image_info["repository"]
        repo_path = f"hummingbird-tech-preview/{repository_name}"

        # Check if repository already exists
        exists = False
        existing_image_name = None
        for repo in repositories:
            if repo.get("repository", {}).get("repository") == repo_path:
                # Ensure display_data exists
                repo_dict = repo.get("repository", {})
                if "display_data" not in repo_dict:
                    repo_dict["display_data"] = {}

                # Extract existing image names from display_data
                display_name = repo_dict.get("display_data", {}).get("name", "")
                existing_image_names = []

                if display_name:
                    # Format: "Project Hummingbird Tech Preview {name1}, {name2} images" or "Project Hummingbird Tech Preview {name} image"
                    # Remove prefix and suffix more carefully
                    name_part = display_name
                    if name_part.startswith("Project Hummingbird Tech Preview "):
                        name_part = name_part[len("Project Hummingbird Tech Preview "):]
                    # Remove " image" or " images" suffix (but only at the end)
                    if name_part.endswith(" images"):
                        name_part = name_part[:-7]  # Remove " images"
                    elif name_part.endswith(" image"):
                        name_part = name_part[:-6]  # Remove " image"
                    # Split by comma to get all image names if multiple
                    existing_image_names = [n.strip() for n in name_part.split(",") if n.strip()]
                    # Clean up any trailing "s" that might be a result of the previous bug
                    # (where " images" was incorrectly parsed, leaving just "s")
                    # Pattern: names ending with a digit followed by "s" (e.g., "aspnet-runtime-9-0s")
                    cleaned_names = []
                    for name in existing_image_names:
                        if name.endswith("s") and len(name) > 1 and name[-2].isdigit():
                            # Likely a bug artifact - remove the trailing "s"
                            cleaned_names.append(name[:-1])
                        else:
                            cleaned_names.append(name)
                    existing_image_names = cleaned_names
                    existing_image_name = existing_image_names[0] if existing_image_names else None

                if not existing_image_name:
                    # Fallback: try to extract from repo path
                    existing_image_name = repo_path.replace("hummingbird-tech-preview/", "")
                    existing_image_names = [existing_image_name]

                # Add the new image name if it's not already in the list
                if image_name not in existing_image_names:
                    existing_image_names.append(image_name)
                    # Update the display_data to include all image names
                    if len(existing_image_names) == 1:
                        display_name_new = f"Project Hummingbird Tech Preview {existing_image_names[0]} image"
                        display_desc_new = f"Project Hummingbird Tech Preview {existing_image_names[0]} image"
                    else:
                        # Sort for consistent ordering
                        sorted_names = sorted(existing_image_names)
                        names_str = ", ".join(sorted_names)
                        display_name_new = f"Project Hummingbird Tech Preview {names_str} images"
                        display_desc_new = f"Project Hummingbird Tech Preview {names_str} images"

                    repo_dict["display_data"]["name"] = display_name_new
                    repo_dict["display_data"]["long_description"] = display_desc_new
                    # Track this update for MR description
                    updated_display_data.append({
                        "repository": repository_name,
                        "image_names": sorted(existing_image_names)
                    })
                    logger.info(
                        f"Updated repository {repo_path} to include {image_name} "
                        f"(now includes: {', '.join(sorted(existing_image_names))})"
                    )

                skipped_images.append(image_info)
                if existing_image_name and existing_image_name != image_name:
                    logger.warning(
                        f"Skipping {image_name} ({repository_name}): repository path {repo_path} "
                        f"already exists and is used by {existing_image_name}"
                    )
                else:
                    logger.info(
                        f"Skipping {image_name} ({repository_name}): repository path {repo_path} "
                        f"already exists in YAML file"
                    )
                exists = True
                break

        if not exists:
            # Add new repository entry
            # Try to use merge keys if ruamel.yaml is available, otherwise expand
            try:
                from ruamel.yaml import YAML
                use_merge = True
            except ImportError:
                use_merge = False
            new_entry = create_repository_entry(image_name, repository_name, use_merge_keys=use_merge)
            repositories.append(new_entry)
            added_images.append(image_info)
            logger.info(f"Added {image_name} ({repository_name}) to YAML update")

    if skipped_images:
        skipped_reasons = []
        for img in skipped_images:
            repo_path = f"hummingbird-tech-preview/{img['repository']}"
            skipped_reasons.append(f"{img['name']} (repo: {img['repository']})")
        logger.info(
            f"Skipped {len(skipped_images)} image(s) that already exist in YAML "
            f"(same repository path): {', '.join(skipped_reasons)}"
        )

    # Re-add merge keys to existing repositories (they were expanded during reading)
    # This ensures all hummingbird-tech-preview repositories use merge keys for deduplication
    repositories_with_merge_keys = []
    for repo in repositories:
        repo_path = repo.get("repository", {}).get("repository", "")
        if repo_path.startswith("hummingbird-tech-preview/"):
            # This is a hummingbird repository - ensure it uses merge keys
            # Extract the fields that should NOT be in the merge (repository-specific fields)
            repo_dict = repo.get("repository", {})
            # Fields that are repository-specific (not in defaults)
            specific_fields = {
                "repository": repo_dict.get("repository"),
                "display_data": repo_dict.get("display_data"),
            }
            # Recreate the repository entry with merge keys
            repository_dict = {
                "<<": "*repo-defaults",  # Merge key marker
                **specific_fields,  # Repository-specific fields
            }
            repositories_with_merge_keys.append({
                "image_type": repo.get("image_type"),
                "base_rhel_version": repo.get("base_rhel_version"),
                "repository": repository_dict,
            })
        else:
            # Not a hummingbird repository, keep as-is
            repositories_with_merge_keys.append(repo)

    data["repositories"] = repositories_with_merge_keys

    # Render from template - template should define all default data
    rendered_yaml = render_yaml_from_template(
        template_path,
        repositories=repositories_with_merge_keys,
    )

    # Normalize for comparison (but preserve newline requirement)
    def normalize_yaml(yaml_str: str) -> str:
        """Normalize YAML string for comparison."""
        lines = yaml_str.split('\n')
        normalized = '\n'.join(line.rstrip() for line in lines).rstrip()
        return normalized

    original_normalized = normalize_yaml(yaml_content)
    rendered_normalized = normalize_yaml(rendered_yaml)

    # Check if content actually changed
    # Also check if original is missing trailing newline (yamllint requirement)
    original_missing_newline = yaml_content and not yaml_content.endswith('\n')
    content_needs_update = (
        original_normalized != rendered_normalized or
        original_missing_newline
    )

    if not content_needs_update and not added_images and not removed_images:
        return yaml_content, [], [], [], []

    # Content changed, return rendered template output
    if not added_images and not removed_images:
        logger.info("YAML structure changed (template rendering), will update file")

    return rendered_yaml, added_images, removed_images, updated_display_data, skipped_images






# ============================================================================
# ReleasePlanAdmission Generation Functions
# ============================================================================

def load_rpa_config(config_path: Path) -> dict[str, Any]:
    """Load RPA configuration from YAML file.

    Args:
        config_path: Path to RPA configuration file

    Returns:
        Dictionary containing RPA configuration
    """
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading RPA config from {config_path}: {e}")
        raise


def get_default_variants() -> list[str]:
    """Get default variants from images/variables.yml.

    Returns:
        List of default variant names
    """
    variables_file = Path("images/variables.yml")
    if not variables_file.exists():
        # Fallback to common defaults
        return ["default"]

    try:
        with open(variables_file, "r") as f:
            variables = yaml.safe_load(f)
        return variables.get("default_variants", ["default"])
    except Exception as e:
        logger.warning(f"Could not read default variants from {variables_file}: {e}")
        return ["default"]


def extract_component_metadata(component_dir: Path, branch: str = "main") -> list[dict[str, Any]]:
    """Extract component metadata for RPA generation.

    Supports both container images (with properties.yml) and RPMs (with .spec files).

    Args:
        component_dir: Path to component directory (e.g., images/ruby or rpms/python)
        branch: Git branch name (default: main)

    Returns:
        List of component metadata dictionaries
    """
    component_metadata = []
    component_name_base = component_dir.name
    properties_file = component_dir / "properties.yml"
    spec_files = list(component_dir.glob("*.spec"))

    # Determine if this is an image (has properties.yml) or RPM (has .spec)
    if properties_file.exists():
        # Image mode: extract variants and detailed metadata
        variants = get_default_variants()

        try:
            with open(properties_file, "r") as f:
                properties = yaml.safe_load(f)

            # variants overrides defaults as the base
            if "variants" in properties:
                variants = properties["variants"]

            # additional_variants extends the base
            if "additional_variants" in properties:
                additional_variants = properties["additional_variants"]
                variants = list(variants) + list(additional_variants)
        except Exception as e:
            logger.warning(f"Error reading {properties_file}: {e}")
            properties = {}

        # Build metadata for each variant
        for variant in variants:
            # Variants can be strings or dicts with a "name" key
            if isinstance(variant, dict):
                variant_name = variant["name"]
            else:
                variant_name = variant

            component_name = sanitize_component_name(f"{component_name_base}--{variant_name}--{branch}")

            # Get repository name (from properties.yml or use component name)
            repository = properties.get("repository", component_name_base)

            # Get tags (from properties.yml or default to latest)
            tags = properties.get("tags", [{"value": "latest"}])

            # Build component metadata entry
            component_entry = {
                "name": f"{component_name_base}-{variant_name}",
                "component_name": component_name,
                "repository": repository,
                "context": str(component_dir),
                "dockerfile": f"{variant_name}/Containerfile",
                "variant": variant_name,
                "tags": tags,
            }

            # Merge in any other properties from properties.yml
            for key, value in properties.items():
                if key not in component_entry:
                    component_entry[key] = value

            component_metadata.append(component_entry)

    elif spec_files:
        # RPM mode: simple metadata with no variants
        component_name = sanitize_component_name(f"{component_name_base}-{branch}")

        component_entry = {
            "name": component_name_base,
            "component_name": component_name,
            "repository": component_name_base,
            "context": str(component_dir),
            "variant": None,
            "tags": [],
        }

        component_metadata.append(component_entry)

    return component_metadata


def filter_components_for_rpa(
    components: list[dict[str, Any]],
    rpa_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Filter components that belong to a specific RPA based on configuration.

    Args:
        components: List of component metadata dictionaries
        rpa_config: RPA configuration dictionary

    Returns:
        Filtered list of components that match the RPA filter criteria
    """
    filtered = []
    component_filter = rpa_config.get("component_filter", {})
    path_prefix = component_filter.get("path_prefix", "")
    exclude_patterns = component_filter.get("exclude_patterns", [])

    for component in components:
        context = component.get("context", "")

        # Check path prefix
        if path_prefix and not context.startswith(path_prefix):
            continue

        # Check exclude patterns
        excluded = False
        for pattern in exclude_patterns:
            if pattern in context or pattern in component.get("name", ""):
                excluded = True
                break
        if excluded:
            continue

        filtered.append(component)

    return filtered


def generate_rpa_yaml(
    rpa_config: dict[str, Any],
    images: list[dict[str, Any]],
    template_dir: Path,
) -> str:
    """Generate ReleasePlanAdmission YAML using Jinja2 template.

    Args:
        rpa_config: RPA configuration dictionary
        images: List of image metadata dictionaries for this RPA
        template_dir: Path to konflux-templates directory

    Returns:
        Rendered RPA YAML string
    """
    # Load the macro template (similar to how generate_konflux_resources.sh does it)
    # Use template from config if specified, otherwise default to release-plan-admission.yml.j2
    template_path = rpa_config.get("template", "macros/release-plan-admission.yml.j2")
    # If path is relative, it's relative to template_dir
    if "/" in template_path or template_path.startswith("macros/"):
        macro_file = template_dir / template_path
    else:
        # If just a filename, assume it's in macros/
        macro_file = template_dir / "macros" / template_path

    if not macro_file.exists():
        raise FileNotFoundError(f"Template file not found: {macro_file}")

    # Use the same approach as generate_konflux_resources.sh:
    # Use the jinja2 CLI tool directly to ensure identical output formatting
    # This matches: jinja2 --strict --format=yaml "${temp_template}" "${temp_variables}"
    import subprocess
    import tempfile
    import yaml

    # Build template variables as YAML (matching generate_konflux_resources.sh)
    # Pass both image_list and component_list for backward compatibility
    template_vars = {
        "branch": rpa_config.get("global", {}).get("branch", "main"),
        "tenant": rpa_config.get("global", {}).get("tenant", "hummingbird-tenant"),
        "release_tenant": rpa_config.get("global", {}).get("release_tenant", "rhtap-releng-tenant"),
        "image_list": images,  # Kept for backward compatibility
        "component_list": images,  # New preferred name
    }

    # Create calling template that invokes the macro
    calling_template = f"""{{%- for single_component_mode in [{str(rpa_config["single_component_mode"]).lower()}] %}}
{{{{ release_plan_admission(
    '{rpa_config.get("name")}',
    '{rpa_config["application_prefix"]}',
    component_list,
    '{rpa_config["release_org"]}',
    single_component_mode,
    '{rpa_config["service_account_name"]}'
) }}}}
{{%- endfor %}}
"""

    # Concatenate macro and calling template (like the shell script does)
    with open(macro_file, "r") as f:
        macro_template = f.read()
    combined_template = macro_template + calling_template

    # Write template and variables to temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
        f.write(combined_template)
        template_path = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(template_vars, f, default_flow_style=False)
        vars_path = f.name

    try:
        # Use jinja2 CLI (same as generate_konflux_resources.sh)
        result = subprocess.run(
            ['jinja2', '--strict', '--format=yaml', template_path, vars_path],
            capture_output=True,
            text=True,
            check=True,
        )
        rendered = result.stdout

        # Remove leading blank lines (yamllint doesn't allow blank lines at start)
        rendered = rendered.lstrip('\n')

        # Ensure the output ends with a newline
        if rendered and not rendered.endswith("\n"):
            rendered += "\n"

        return rendered
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to render RPA template: {e.stderr}\n"
            f"Template: {template_path}\nVariables: {vars_path}"
        ) from e
    finally:
        import os
        os.unlink(template_path)
        os.unlink(vars_path)


def generate_and_submit_rpas(
    merged_components: list[dict[str, Any]],
    pyxis_mr_id: int | str,
    gitlab_client: GitLabClient | None,
    konflux_repo_path: str,
    pyxis_project_path: str,
    konflux_repo_url: str | None = None,
    rpa_config_path: Path | None = None,
    template_dir: Path | None = None,
    components_dir: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    preview_rpa_dir: Path | None = None,
) -> int | None:
    """Generate ReleasePlanAdmissions for components and create MR in konflux-release-data repo.

    This function is idempotent - it compares generated content with existing files
    and only creates/updates MRs if there are actual changes.

    Args:
        merged_components: List of component info dicts with 'name' key
        pyxis_mr_id: ID for branch naming (pyxis MR ID or "direct" for skip mode)
        gitlab_client: GitLabClient instance (can be None if preview_rpa_dir is set)
        konflux_repo_path: GitLab project path for konflux-release-data (e.g., "org/konflux-release-data")
        konflux_repo_url: Optional GitLab URL (defaults to gitlab_client's URL)
        rpa_config_path: Path to RPA configuration file
        template_dir: Path to konflux-templates directory
        components_dir: Path to components directory (inferred from config if not provided)
        dry_run: If True, don't create MRs, just log what would be done
        preview_rpa_dir: If set, write RPA files to this directory and stop (no remote operations)
    """
    if not merged_components:
        logger.debug("No merged components to generate RPAs for")
        return None

    # Set defaults
    if rpa_config_path is None:
        rpa_config_path = Path("ci/konflux_rpa_config.yml")
    if template_dir is None:
        template_dir = Path("konflux-templates")
    if konflux_repo_url is None and gitlab_client is not None:
        konflux_repo_url = gitlab_client.api_url.replace("/api/v4", "")

    # Load RPA configuration
    try:
        rpa_config = load_rpa_config(rpa_config_path)
    except Exception as e:
        logger.error(f"Failed to load RPA configuration: {e}")
        return None

    # Get konflux repo project ID (skip in preview mode)
    konflux_project_id = None
    if preview_rpa_dir is None:
        assert gitlab_client is not None, "gitlab_client required when not in preview mode"
        try:
            konflux_project_id = gitlab_client.get_project_id(konflux_repo_path)
            logger.debug(f"Konflux repo project ID: {konflux_project_id}")
        except Exception as e:
            logger.error(f"Error getting konflux repo project ID: {e}")
            return None

    # Extract component metadata for all merged components
    all_component_metadata = []

    # Determine components directory from config if not provided
    if components_dir is None:
        # Try to infer from RPA config's component_filter.path_prefix
        rpas = rpa_config.get("rpas", [])
        path_prefixes = set()
        for rpa in rpas:
            component_filter = rpa.get("component_filter", {})
            path_prefix = component_filter.get("path_prefix", "")
            if path_prefix:
                path_prefixes.add(path_prefix.rstrip("/"))
        if len(path_prefixes) == 1:
            components_dir = Path(path_prefixes.pop())
        else:
            components_dir = Path("images")

    for component_info in merged_components:
        component_name = component_info.get("name")
        if not component_name:
            continue

        # Look in the components directory
        component_dir = components_dir / component_name
        if not component_dir.exists():
            # Fall back to ci/<components_dir> (e.g., ci/images/)
            component_dir = Path("ci") / components_dir / component_name

        if not component_dir.exists():
            logger.warning(f"Component directory not found for {component_name}, skipping RPA generation")
            continue

        try:
            metadata = extract_component_metadata(component_dir, branch=rpa_config.get("global", {}).get("branch", "main"))
            all_component_metadata.extend(metadata)
        except Exception as e:
            logger.warning(f"Error extracting metadata for {component_name}: {e}")
            continue

    if not all_component_metadata:
        logger.info("No component metadata extracted, skipping RPA generation")
        return None

    # Generate RPAs for each configured RPA
    rpa_files_to_update: dict[str, str] = {}  # target_file -> yaml_content
    branch_name = f"{KONFLUX_BRANCH_PREFIX}{pyxis_mr_id}"

    for rpa in rpa_config.get("rpas", []):
        rpa_name = rpa["name"]
        logger.debug(f"Processing RPA: {rpa_name}")

        # Filter components for this RPA
        filtered_components = filter_components_for_rpa(all_component_metadata, rpa)

        if not filtered_components:
            logger.debug(f"No components match filter for RPA {rpa_name}, skipping")
            continue

        logger.info(f"Generating RPA {rpa_name} with {len(filtered_components)} component(s)")

        try:
            rpa_yaml = generate_rpa_yaml(rpa, filtered_components, template_dir)
            target_file = rpa["target_file"]
            rpa_files_to_update[target_file] = rpa_yaml
        except Exception as e:
            logger.error(f"Error generating RPA {rpa_name}: {e}")
            continue

    if not rpa_files_to_update:
        logger.info("No RPA files to update")
        return None

    # Preview mode: write files locally and stop
    if preview_rpa_dir is not None:
        preview_rpa_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[PREVIEW] Writing {len(rpa_files_to_update)} RPA file(s) to {preview_rpa_dir}/")
        for target_file, content in rpa_files_to_update.items():
            # Preserve directory structure from target_file
            local_path = preview_rpa_dir / target_file
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_text(content)
            logger.info(f"[PREVIEW] Wrote {local_path}")
        logger.info(f"[PREVIEW] RPA files written to {preview_rpa_dir}/ - verify and re-run without --preview-rpa to submit")
        return None

    if dry_run:
        logger.info(f"[DRY RUN] Would create/update {len(rpa_files_to_update)} RPA file(s) in {konflux_repo_path}")
        for target_file, content in rpa_files_to_update.items():
            logger.info(f"[DRY RUN] Would update {target_file}")
        return None

    # Check if files actually need updates by comparing with main branch content
    # This avoids creating a branch unnecessarily
    files_need_update = []
    components_added: set[str] = set()
    components_removed: set[str] = set()

    def _extract_rpa_component_names(yaml_str: str) -> set[str]:
        """Extract component names from RPA YAML content."""
        try:
            data = yaml.safe_load(yaml_str)
            if not data:
                return set()
            components = (
                data.get("spec", {})
                .get("data", {})
                .get("mapping", {})
                .get("components", [])
            ) or []
            return {c.get("name", "") for c in components if isinstance(c, dict) and c.get("name")}
        except Exception:
            return set()

    assert gitlab_client is not None, "gitlab_client required for remote operations"
    assert konflux_project_id is not None, "konflux_project_id required for remote operations"
    for target_file, yaml_content in rpa_files_to_update.items():
        try:
            # Read existing file from main branch
            main_content_decoded: str | None = None
            try:
                existing_content = gitlab_client.get_file_content(konflux_project_id, target_file, ref="main")
                main_content_decoded = existing_content.decode("utf-8") if isinstance(existing_content, bytes) else existing_content
            except requests.HTTPError as e:
                if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                    # File doesn't exist on main, needs to be created
                    files_need_update.append(target_file)
                    # All components in the new file are "added"
                    components_added.update(_extract_rpa_component_names(yaml_content))
                    continue
                else:
                    raise

            # Compare content
            if main_content_decoded is None or main_content_decoded.strip() != yaml_content.strip():
                files_need_update.append(target_file)
                # Diff component lists to track what actually changed
                old_components = _extract_rpa_component_names(main_content_decoded or "")
                new_components = _extract_rpa_component_names(yaml_content)
                components_added.update(new_components - old_components)
                components_removed.update(old_components - new_components)
            else:
                logger.debug(f"File {target_file} is already up-to-date on main branch")
        except Exception as e:
            logger.warning(f"Error checking {target_file} on main branch: {e}, will include it for update")
            files_need_update.append(target_file)

    if not files_need_update:
        if force:
            logger.info("No files need updates (all already up-to-date), but force mode enabled - will still create/update MR")
        else:
            logger.info("No files need updates (all already up-to-date on main branch)")
            return None

    # Create or update branch in konflux-release-data repo
    try:
        # Check if branch exists by trying to get a file
        branch_exists = False
        try:
            gitlab_client.get_file_content(konflux_project_id, ".gitlab-ci.yml", ref=branch_name)
            branch_exists = True
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                branch_exists = False
            else:
                raise

        if not branch_exists:
            # Create branch from main
            try:
                gitlab_client.create_branch(konflux_project_id, branch_name, "main")
                logger.info(f"Created branch {branch_name} in {konflux_repo_path}")
            except requests.HTTPError as e:
                if hasattr(e, "response") and e.response is not None:
                    status_code = e.response.status_code
                    if status_code == 400:
                        # Branch might have been created between check and create, or already exists
                        logger.info(f"Branch {branch_name} already exists, will update it")
                        branch_exists = True
                    elif status_code == 403:
                        logger.error(
                            f"Permission denied: GitLab token lacks permission to create branches in {konflux_repo_path} (HTTP 403). "
                            f"Please ensure your token has 'api' scope with 'write_repository' permission for this repository. "
                            f"You may need to manually create the branch '{branch_name}' from 'main' in the GitLab UI."
                        )
                        return None
                    else:
                        logger.error(f"Error creating branch {branch_name} (HTTP {status_code}): {e}")
                        return None
                else:
                    logger.error(f"Error creating branch {branch_name}: {e}")
                    return None
            except Exception as e:
                logger.error(f"Error creating branch {branch_name}: {e}")
                return None

        # Update or create each RPA file that needs updates
        files_updated = []
        for target_file in files_need_update:
            yaml_content = rpa_files_to_update[target_file]
            try:
                # Read existing file if it exists on the branch
                branch_content_decoded: str | None = None
                try:
                    existing_content = gitlab_client.get_file_content(konflux_project_id, target_file, ref=branch_name)
                    branch_content_decoded = existing_content.decode("utf-8") if isinstance(existing_content, bytes) else existing_content
                except requests.HTTPError as e:
                    if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                        branch_content_decoded = None
                    else:
                        raise

                # Compare content (double-check, though we already checked against main)
                if branch_content_decoded and branch_content_decoded.strip() == yaml_content.strip():
                    logger.debug(f"File {target_file} is already up-to-date on branch")
                    continue

                # Create or update file
                gitlab_client.create_or_update_file(
                    konflux_project_id,
                    target_file,
                    yaml_content,
                    branch_name,
                    f"Update {target_file} for images from pyxis MR {pyxis_mr_id}",
                )
                files_updated.append(target_file)
                logger.info(f"Updated {target_file}")
            except Exception as e:
                logger.error(f"Error updating {target_file}: {e}")
                continue

        if not files_updated:
            if force:
                logger.info("No files were updated (all already up-to-date), but force mode enabled - will still create/update MR")
            else:
                logger.info("No files were updated (all already up-to-date)")
                # Clean up branch if no changes
                try:
                    # Note: GitLab API doesn't have a direct delete branch endpoint in the merge requests API
                    # We could leave the branch or delete it via repository API
                    logger.debug(f"Branch {branch_name} has no changes, but leaving it for now")
                except Exception:
                    pass
                return None

        # Create or update MR (force mode will create even if files_updated is empty)
        mr_title = f"Hummingbird updates for images from {pyxis_project_path} MR {pyxis_mr_id}"
        if files_updated:
            files_section = f"""**Updated RPA files ({len(files_updated)}):**
{chr(10).join(f"- {f}" for f in files_updated)}"""
        else:
            files_section = "**Note:** Force mode enabled - no files were updated (all already up-to-date)"
        # Build component changes section for MR description
        changes_parts = []
        if components_added:
            sorted_added = sorted(components_added)
            changes_parts.append(f"**Components added ({len(sorted_added)}):** {', '.join(sorted_added)}")
        if components_removed:
            sorted_removed = sorted(components_removed)
            changes_parts.append(f"**Components removed ({len(sorted_removed)}):** {', '.join(sorted_removed)}")
        if not changes_parts:
            changes_parts.append(f"**Components ({len(merged_components)} total):** no component additions or removals (non-component changes only)")
        changes_section = "\n\n".join(changes_parts)

        mr_description = f"""Updates ReleasePlanAdmission resources for components.

{files_section}

{changes_section}

**Total components:** {len(merged_components)}

Generated by: ci/onboard_components_to_releng.py
"""

        # Check if MR already exists
        existing_mrs = gitlab_client.list_merge_requests(
            konflux_project_id,
            state="opened",
            source_branch=branch_name,
        )

        if existing_mrs:
            mr = existing_mrs[0]
            konflux_mr_id = mr["iid"]
            logger.debug(f"Updating existing MR {konflux_mr_id} in {konflux_repo_path}")
            gitlab_client.update_merge_request(
                konflux_project_id,
                konflux_mr_id,
                title=mr_title,
                description=mr_description,
                merge_when_pipeline_succeeds=True,
            )
        else:
            logger.debug(f"Creating MR in {konflux_repo_path}")
            mr = gitlab_client.create_merge_request(
                konflux_project_id,
                branch_name,
                "main",
                mr_title,
                mr_description,
                merge_when_pipeline_succeeds=True,
            )
            konflux_mr_id = mr["iid"]
            logger.debug(f"Created konflux MR {konflux_mr_id} in {konflux_repo_path}: {mr.get('web_url', '')}")

            # Wait for CI pipeline to be triggered after MR creation
            import time
            logger.debug("Waiting for CI pipeline to be triggered after konflux MR creation...")
            time.sleep(3)  # Wait 3 seconds for GitLab to trigger pipeline

            # Check for new pipeline
            try:
                pipelines = gitlab_client.get_merge_request_pipelines(konflux_project_id, konflux_mr_id)
                if pipelines:
                    latest_pipeline = pipelines[0]
                    pipeline_status = latest_pipeline.get("status", "unknown")
                    pipeline_web_url = latest_pipeline.get("web_url", "")

                    status_emoji = {
                        "success": "✓",
                        "failed": "✗",
                        "running": "⟳",
                        "pending": "⏳",
                        "canceled": "⊘",
                        "skipped": "⊘",
                    }.get(pipeline_status, "?")

                    logger.debug(
                        f"Konflux MR {konflux_mr_id} CI pipeline status: {status_emoji} {pipeline_status}"
                        + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                    )
                else:
                    # No pipeline yet, wait a bit more and check again
                    logger.debug("No konflux pipeline visible yet, waiting additional time...")
                    time.sleep(5)
                    pipelines = gitlab_client.get_merge_request_pipelines(konflux_project_id, konflux_mr_id)
                    if pipelines:
                        latest_pipeline = pipelines[0]
                        pipeline_status = latest_pipeline.get("status", "unknown")
                        pipeline_web_url = latest_pipeline.get("web_url", "")

                        status_emoji = {
                            "success": "✓",
                            "failed": "✗",
                            "running": "⟳",
                            "pending": "⏳",
                            "canceled": "⊘",
                            "skipped": "⊘",
                        }.get(pipeline_status, "?")

                        logger.debug(
                            f"Konflux MR {konflux_mr_id} CI pipeline status: {status_emoji} {pipeline_status}"
                            + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                        )
                    else:
                        logger.debug(f"Konflux MR {konflux_mr_id} pipeline not yet visible (may start shortly)")
            except Exception as e:
                logger.debug(f"Could not check pipeline status for newly created konflux MR {konflux_mr_id}: {e}")

        return konflux_mr_id

    except Exception as e:
        logger.error(f"Error generating and submitting RPAs: {e}", exc_info=True)
        return None


def expand_merge_keys_from_yaml(yaml_content: str, template_path: Path) -> str:
    """Expand merge keys in YAML content for PyYAML compatibility.

    This is useful when you need to parse YAML with merge keys using PyYAML.
    Returns YAML content with merge keys expanded.

    The function reads the YAML, expands any merge keys by looking up the
    repository-defaults anchor, and returns expanded YAML that PyYAML can parse.

    Also handles ruamel.yaml special objects by converting them to plain Python objects.
    """
    # First, check if the YAML contains ruamel.yaml special objects
    # If so, we need to parse with ruamel.yaml and convert to plain objects
    if '!!python/object/new:ruamel.yaml' in yaml_content or '!!python/object:ruamel.yaml' in yaml_content:
        try:
            from ruamel.yaml import YAML
            yaml_obj = YAML()
            yaml_obj.allow_duplicate_keys = True
            data = yaml_obj.load(yaml_content)
            if data:
                # Convert ruamel.yaml objects to plain Python objects
                def to_plain_python(obj):
                    """Convert ruamel.yaml objects to plain Python objects."""
                    # Check if it's a ruamel.yaml scalar string
                    if hasattr(obj, 'value'):
                        # ruamel.yaml scalar strings have a 'value' attribute
                        obj = obj.value
                    elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
                        # Convert other ruamel.yaml objects to strings
                        obj = str(obj)

                    if isinstance(obj, dict):
                        return {k: to_plain_python(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [to_plain_python(item) for item in obj]
                    else:
                        return obj

                plain_data = to_plain_python(data)
                # Expand merge keys if needed
                expanded = _expand_existing_merge_keys(plain_data)
                # Use PyYAML to dump, which will create plain YAML
                return yaml.dump(expanded, default_flow_style=False, sort_keys=False)
        except ImportError:
            # ruamel.yaml not available, continue with normal processing
            pass
        except Exception as e:
            # If conversion fails, continue with normal processing
            logger.debug(f"Failed to convert ruamel.yaml objects: {e}")
    # Check if the YAML has merge keys or alias references
    has_merge_keys = '<<: *repo-defaults' in yaml_content
    has_team_alias = '*team-contacts' in yaml_content

    if not has_merge_keys and not has_team_alias:
        # No merge keys or aliases, return as-is
        return yaml_content

    # Check if anchors are defined
    has_repo_anchor = 'repository-defaults: &repo-defaults' in yaml_content or 'repository-defaults:&repo-defaults' in yaml_content
    has_team_anchor = 'hummingbird-team: &team-contacts' in yaml_content or 'hummingbird-team:&team-contacts' in yaml_content

    # If anchors are not defined, inject them
    if (has_merge_keys and not has_repo_anchor) or (has_team_alias and not has_team_anchor):
        # Get the anchor definitions from create_initial_yaml_structure
        initial_structure = create_initial_yaml_structure(template_path)

        # Extract both anchors if needed
        team_anchor_lines = []
        repo_anchor_lines = []

        if has_team_alias and not has_team_anchor:
            in_anchor = False
            for line in initial_structure.split('\n'):
                if 'hummingbird-team: &team-contacts' in line:
                    in_anchor = True
                    team_anchor_lines.append(line)
                elif in_anchor:
                    if line.strip() and not (line.startswith(' ') or line.startswith('\t')):
                        break
                    team_anchor_lines.append(line)

        if has_merge_keys and not has_repo_anchor:
            in_anchor = False
            for line in initial_structure.split('\n'):
                if 'repository-defaults: &repo-defaults' in line:
                    in_anchor = True
                    repo_anchor_lines.append(line)
                elif in_anchor:
                    if line.strip() and not (line.startswith(' ') or line.startswith('\t')):
                        break
                    repo_anchor_lines.append(line)

        # Inject anchors into the YAML content
        lines = yaml_content.split('\n')
        injected_lines = []
        team_anchor_injected = False
        repo_anchor_injected = False

        for i, line in enumerate(lines):
            if i == 0 and line.strip() == '---':
                injected_lines.append(line)
                continue

            # Inject hummingbird-team anchor first if needed
            if not team_anchor_injected and team_anchor_lines:
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    # Inject before this line
                    for anchor_line in team_anchor_lines:
                        injected_lines.append(anchor_line)
                    team_anchor_injected = True

            # Inject repository-defaults anchor after team anchor if needed
            if team_anchor_injected and not repo_anchor_injected and repo_anchor_lines:
                if 'repositories:' in line or (line.strip() and not line.startswith(' ') and not line.startswith('\t') and 'hummingbird-team:' not in line):
                    # Inject before this line
                    for anchor_line in repo_anchor_lines:
                        injected_lines.append(anchor_line)
                    repo_anchor_injected = True

            injected_lines.append(line)

        # If anchors weren't injected in the loop, inject at the beginning
        if not team_anchor_injected and team_anchor_lines:
            if lines[0].strip() == '---':
                injected_lines = [lines[0]] + team_anchor_lines + injected_lines[1:]
            else:
                injected_lines = team_anchor_lines + injected_lines
            team_anchor_injected = True

        if not repo_anchor_injected and repo_anchor_lines:
            # Find where to inject (after team anchor or at beginning)
            insert_pos = 0
            if lines[0].strip() == '---':
                insert_pos = 1
            if team_anchor_injected:
                # Find the end of team anchor
                for i, line in enumerate(injected_lines):
                    if 'hummingbird-team:' in line:
                        # Find the end of this anchor block
                        for j in range(i + 1, len(injected_lines)):
                            if injected_lines[j].strip() and not (injected_lines[j].startswith(' ') or injected_lines[j].startswith('\t')):
                                insert_pos = j
                                break
                        break

            injected_lines = injected_lines[:insert_pos] + repo_anchor_lines + injected_lines[insert_pos:]

        yaml_content = '\n'.join(injected_lines)

    # Now use ruamel.yaml to load and expand merge keys
    try:
        from ruamel.yaml import YAML  # type: ignore[import-not-found]

        yaml_obj = YAML()
        yaml_obj.allow_duplicate_keys = True
        # ruamel.yaml automatically expands merge keys when loading
        data = yaml_obj.load(yaml_content)
        if data:
            # The data already has merge keys expanded by ruamel.yaml
            # But we need to ensure all nested merge keys are expanded too
            expanded = _expand_existing_merge_keys(data)

            # Convert to plain Python dict/list to break anchor references
            # This prevents ruamel.yaml from recreating alias references when dumping
            def to_plain_python(obj):
                """Convert ruamel.yaml objects to plain Python objects."""
                # Check if it's a ruamel.yaml scalar string
                if hasattr(obj, 'value'):
                    # ruamel.yaml scalar strings have a 'value' attribute
                    obj = obj.value
                elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
                    # Convert other ruamel.yaml objects to strings
                    obj = str(obj)

                if isinstance(obj, dict):
                    return {k: to_plain_python(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [to_plain_python(item) for item in obj]
                else:
                    return obj

            plain_data = to_plain_python(expanded)

            # Use PyYAML to dump instead of ruamel.yaml, since PyYAML doesn't support
            # anchors/aliases and will just dump the plain values
            return yaml.dump(plain_data, default_flow_style=False, sort_keys=False)
    except ImportError:
        # ruamel.yaml not available, can't expand merge keys
        # Return as-is and let the caller handle it
        pass
    except Exception as e:
        # If loading fails, log and return original (caller should handle)
        logger.debug(f"Failed to expand merge keys: {e}")
        pass

    # Fallback: return original content
    # The caller should use ruamel.yaml if available
    return yaml_content


def _expand_existing_merge_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Expand any existing merge keys in the data structure.

    This is used when reading existing YAML files that might have merge keys.
    We expand them so we can work with the data in Python dicts.
    """
    # Get the anchors if they exist
    repo_defaults = data.get("repository-defaults", {})
    team_contacts = data.get("hummingbird-team", [])

    def expand_dict(d: dict[str, Any]) -> dict[str, Any]:
        """Recursively expand merge keys in a dictionary."""
        if not isinstance(d, dict):
            return d

        result: dict[str, Any] = {}
        merge_values: dict[str, Any] = {}

        for key, value in d.items():
            if key == "<<" and isinstance(value, str) and value.startswith("*"):
                # This is a merge key reference - expand it
                anchor_name = value[1:]  # Remove the *
                if anchor_name == "repo-defaults":
                    # Merge in the repository defaults
                    merge_values.update(repo_defaults)
                elif anchor_name == "team-contacts":
                    # Merge in the team contacts
                    merge_values["contacts"] = team_contacts
            else:
                if isinstance(value, dict):
                    result[key] = expand_dict(value)
                elif isinstance(value, list):
                    result[key] = [expand_dict(item) if isinstance(item, dict) else item for item in value]
                else:
                    # Check if value is an alias reference (e.g., *team-contacts)
                    if isinstance(value, str) and value.startswith("*"):
                        anchor_name = value[1:]
                        if anchor_name == "team-contacts":
                            result[key] = team_contacts
                        else:
                            result[key] = value
                    else:
                        result[key] = value

        # Merge the collected values (merge keys come first, then override with specific values)
        return {**merge_values, **result}

    # Expand merge keys in the entire data structure
    expanded_data = expand_dict(data)

    # Also expand alias references in the repository-defaults anchor itself
    if "repository-defaults" in expanded_data:
        expanded_data["repository-defaults"] = expand_dict(expanded_data["repository-defaults"])

    # Also ensure repositories are properly expanded
    if "repositories" in expanded_data and expanded_data["repositories"] is not None:
        expanded_repos = []
        for repo in expanded_data["repositories"]:
            if isinstance(repo, dict) and "repository" in repo:
                # Ensure the repository dict is fully expanded
                if isinstance(repo["repository"], dict):
                    repo["repository"] = expand_dict(repo["repository"])
            expanded_repos.append(repo)
        expanded_data["repositories"] = expanded_repos

    return expanded_data




def clone_or_update_repo(
    repo_url: str,
    target_dir: Path,
    branch: str = "main",
) -> None:
    """Clone or update the pyxis-repo-configs repository."""
    if target_dir.exists():
        logger.info(f"Updating existing repository at {target_dir}")
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", branch],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "reset", "--hard", f"origin/{branch}"],
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
    else:
        logger.info(f"Cloning repository to {target_dir}")
        subprocess.run(
            ["git", "clone", "--branch", branch, repo_url, str(target_dir)],
            check=True,
            capture_output=True,
        )


def onboard_images_batch(
    images_to_onboard: list[dict[str, Any]],
    gitlab_client: GitLabClient,
    project_id: int,
    template_path: Path,
    pyxis_file_path: str,
    all_local_images: list[dict[str, Any]] | None = None,
    dry_run: bool = False,
    force: bool = False,
    force_rpa: bool = False,
    pyxis_project_path: str | None = None,
    konflux_repo_path: str | None = None,
    konflux_repo_url: str | None = None,
    rpa_config_path: Path | None = None,
    rpa_template_dir: Path | None = None,
    wait_for_post_merge_pipeline: bool = False,
    post_merge_pipeline_timeout: int = 600,
    wait_for_mr_pipeline: bool = True,
    mr_pipeline_timeout: int = 3600,
) -> None:
    """Onboard multiple images in a single MR to pyxis-repo-configs.

    This function is stateless - it queries the current YAML state from GitLab
    and determines what changes are needed without relying on a tracking file.

    Args:
        images_to_onboard: Images to add to the YAML
        all_local_images: All images that exist locally (used to detect removals)
    """
    if not images_to_onboard and not all_local_images:
        logger.info("No images to process")
        return

    branch_name = PYXIS_BRANCH_NAME
    image_names = [img["name"] for img in images_to_onboard]
    if image_names:
        logger.info(f"Checking {len(images_to_onboard)} image(s) for onboarding (some may already exist in YAML): {', '.join(image_names)}")
    else:
        logger.info("No new images to check (checking for removals only)")

    # Check if branch already exists and has an open MR
    branch_exists = False
    has_open_mr = False
    try:
        # Try to get file from the branch to see if it exists
        gitlab_client.get_file_content(project_id, pyxis_file_path, ref=branch_name)
        branch_exists = True

        # Check if there's an open MR for this branch
        existing_mrs = gitlab_client.list_merge_requests(
            project_id,
            state="opened",
            source_branch=branch_name,
        )
        if existing_mrs:
            has_open_mr = True
            mr = existing_mrs[0]
            mr_id = mr['iid']
            logger.info(f"Branch {branch_name} already exists with open MR {mr_id}, using it")

            # Check for merge conflicts
            merge_status = mr.get('merge_status', 'unknown')
            if merge_status == 'cannot_be_merged':
                logger.error(
                    f"MR {mr_id} has merge conflicts and cannot be merged automatically. "
                    f"This usually happens when the target file was updated directly in the main branch. "
                    f"Attempting to rebase the branch to resolve conflicts..."
                )
                try:
                    rebase_result = gitlab_client.rebase_merge_request(project_id, mr_id)
                    logger.info(f"Rebase initiated for MR {mr_id}. Status: {rebase_result.get('rebase_in_progress', False)}")
                    # Wait a moment for rebase to start, then check status again
                    import time
                    time.sleep(2)
                    # Refresh MR status
                    mr = gitlab_client.get_merge_request(project_id, mr_id)
                    merge_status = mr.get('merge_status', 'unknown')
                    if merge_status == 'cannot_be_merged':
                        logger.error(
                            f"MR {mr_id} still has conflicts after rebase attempt. "
                            f"Please resolve conflicts manually in GitLab or rebase the branch manually."
                        )
                        raise RuntimeError(
                            f"MR {mr_id} has unresolved merge conflicts. "
                            f"The target file was likely updated directly in the main branch. "
                            f"Please resolve conflicts manually in GitLab before continuing."
                        )
                    elif merge_status == 'checking':
                        logger.info(f"MR {mr_id} rebase in progress, merge status is being checked...")
                    else:
                        logger.info(f"MR {mr_id} rebase completed, merge status: {merge_status}")
                except RuntimeError:
                    # Re-raise RuntimeError (conflicts still present)
                    raise
                except Exception as e:
                    logger.error(
                        f"Failed to rebase MR {mr_id}: {e}. "
                        f"Please resolve conflicts manually in GitLab."
                    )
                    raise RuntimeError(
                        f"Failed to rebase MR {mr_id} to resolve conflicts: {e}. "
                        f"Please resolve conflicts manually in GitLab before continuing."
                    ) from e
            elif merge_status == 'checking':
                logger.info(f"MR {mr_id} merge status is being checked...")
            elif merge_status == 'can_be_merged':
                logger.debug(f"MR {mr_id} can be merged (no conflicts)")
        else:
            logger.info(f"Branch {branch_name} exists but has no open MR (was closed/merged), will use main and recreate")
    except requests.HTTPError as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
            # Branch doesn't exist, will create it
            pass
        else:
            # Other error, log and continue
            logger.warning(f"Error checking branch {branch_name}: {e}")

    # Get current YAML file content
    # Use branch only if it exists AND has an open MR, otherwise use main
    if branch_exists and has_open_mr:
        ref = branch_name
    else:
        ref = "main"
        # If branch exists but no open MR, we'll update it (not create)
        # Keep branch_exists = True so we update the existing branch
    try:
        yaml_content = gitlab_client.get_file_content(project_id, pyxis_file_path, ref=ref)
    except requests.HTTPError as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
            # File doesn't exist, create initial structure
            logger.info(
                f"File {pyxis_file_path} does not exist, creating initial structure",
            )
            yaml_content = create_initial_yaml_structure(template_path)
        else:
            logger.error(f"Error getting YAML file content: {e}")
            return
    except Exception as e:
        logger.error(f"Error getting YAML file content: {e}")
        return

    # Build set of valid repository names (all images that exist locally)
    valid_repository_names = None
    if all_local_images is not None:
        valid_repository_names = {img["repository"] for img in all_local_images}

    # Update YAML file with all new images and remove deleted ones
    updated_content, added_images, removed_images, updated_display_data, skipped_images = update_yaml_file(
        yaml_content,
        images_to_onboard,
        template_path,
        valid_repository_names=valid_repository_names,
    )

    # Normalize YAML strings for comparison (strip trailing whitespace, normalize line endings)
    def normalize_yaml(yaml_str: str) -> str:
        """Normalize YAML string for comparison."""
        lines = yaml_str.split('\n')
        # Remove trailing whitespace and empty lines at end
        normalized = '\n'.join(line.rstrip() for line in lines).rstrip()
        return normalized

    original_normalized = normalize_yaml(yaml_content)
    updated_normalized = normalize_yaml(updated_content)

    # Check if original is missing trailing newline (yamllint requirement)
    original_missing_newline = yaml_content and not yaml_content.endswith('\n')

    content_changed = (
        original_normalized != updated_normalized or
        original_missing_newline
    )

    # Handle dry-run mode - show what would be done
    if dry_run:
        logger.info("DRY RUN: Analyzing what changes would be made...")
        if added_images:
            logger.info(f"DRY RUN: Would add {len(added_images)} image(s) to YAML file:")
            for img in added_images:
                logger.info(f"  + {img['name']} ({img['repository']})")
        if removed_images:
            logger.info(f"DRY RUN: Would remove {len(removed_images)} image(s) from YAML file:")
            for img in removed_images:
                logger.info(f"  - {img['name']} ({img['repository']})")
        if skipped_images:
            logger.info(f"DRY RUN: {len(skipped_images)} image(s) already exist in YAML (no changes needed):")
            for img in skipped_images:
                logger.info(f"  = {img['name']} ({img['repository']})")
        if content_changed and not added_images and not removed_images:
            logger.info("DRY RUN: YAML content would change (e.g., format/structure update)")
        if not content_changed and not added_images and not removed_images:
            logger.info("DRY RUN: No changes needed - all images already onboarded")
        return

    # Log summary
    if added_images:
        logger.info(f"Will add {len(added_images)} image(s) to YAML file")
    if removed_images:
        logger.info(f"Will remove {len(removed_images)} image(s) from YAML file")
    if content_changed and not added_images and not removed_images:
        logger.info("YAML content changed (e.g., format/structure update)")

    # If no changes, return early (unless force mode)
    if not content_changed and not force:
        if images_to_onboard:
            logger.info("No changes needed (all images already exist in YAML and none removed) (use --force to override)")
        else:
            logger.info("No changes needed (no new images and none removed) (use --force to override)")

        # Even if no pyxis changes, generate RPAs if --force-rpa is set
        if force_rpa and konflux_repo_path and all_local_images:
            logger.info("Force RPA mode: regenerating RPAs despite no pyxis changes")
            # Find the most recent merged pyxis MR to use for branch naming
            try:
                merged_mrs = gitlab_client.list_merge_requests(
                    project_id,
                    state="merged",
                    source_branch=branch_name,
                )
                if merged_mrs:
                    # Use the most recent merged MR ID
                    pyxis_mr_id = merged_mrs[0]["iid"]
                    logger.info(f"Using most recent merged pyxis MR {pyxis_mr_id} for RPA branch naming")
                else:
                    # No merged MRs found, use a timestamp-based ID
                    import time
                    pyxis_mr_id = int(time.time())
                    logger.info(f"No merged pyxis MRs found, using timestamp {pyxis_mr_id} for RPA branch naming")

                merged_image_names = [{"name": img["name"]} for img in all_local_images]
                logger.info(f"Generating ReleasePlanAdmissions for {len(merged_image_names)} image(s)...")
                generate_and_submit_rpas(
                    merged_image_names,
                    pyxis_mr_id,
                    gitlab_client,
                    konflux_repo_path,
                    pyxis_project_path or "releng/pyxis-repo-configs",
                    konflux_repo_url,
                    rpa_config_path,
                    rpa_template_dir,
                    dry_run=dry_run,
                    force=True,  # Force update even if content seems unchanged
                )
            except Exception as e:
                logger.error(f"Error generating RPAs in force-rpa mode: {e}", exc_info=True)
            return
        # If branch exists but no changes, check if MR exists and ensure auto-merge is enabled
        if branch_exists:
            existing_mrs = gitlab_client.list_merge_requests(
                project_id,
                state="opened",
                source_branch=branch_name,
            )
            if existing_mrs:
                mr = existing_mrs[0]
                mr_id = mr["iid"]
                logger.info(f"MR {mr_id} already exists")

                # Ensure auto-merge is enabled even when there are no changes
                try:
                    logger.debug(f"Attempting to set auto-merge for MR {mr_id}")
                    result = gitlab_client.update_merge_request(
                        project_id,
                        mr_id,
                        merge_when_pipeline_succeeds=True,
                    )
                    # Note: GitLab may return merge_when_pipeline_succeeds=False if requirements
                    # aren't met yet (e.g., pending approvals), but the setting request was sent.
                    # The setting may still be applied and will activate when all requirements are satisfied.
                    merge_when_set = result.get('merge_when_pipeline_succeeds')
                    auto_merge_set = result.get('auto_merge')
                    logger.debug(f"MR {mr_id} update response: auto_merge={auto_merge_set}, merge_when_pipeline_succeeds={merge_when_set}")

                    if merge_when_set or auto_merge_set:
                        logger.info(f"✓ Auto-merge enabled for MR {mr_id}")
                    else:
                        # The setting was sent but GitLab returned False - this usually means
                        # requirements aren't met yet (e.g., pending approvals). The setting request
                        # was sent and may still be applied; it will activate when requirements are met.
                        # Check the MR in the GitLab UI to verify if auto-merge is actually enabled.
                        logger.info(f"✓ Auto-merge setting request sent for MR {mr_id} (GitLab returned False, likely due to pending approvals - check UI to verify)")
                except Exception as e:
                    logger.warning(f"Could not update auto-merge setting for MR {mr_id}: {e}", exc_info=True)

                # Check CI pipeline status
                pipeline_success = False
                try:
                    pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
                    if pipelines:
                        # Get the latest pipeline (pipelines are usually sorted by creation date, newest first)
                        latest_pipeline = pipelines[0]
                        pipeline_status = latest_pipeline.get("status", "unknown")
                        pipeline_web_url = latest_pipeline.get("web_url", "")

                        status_emoji = {
                            "success": "✓",
                            "failed": "✗",
                            "running": "⟳",
                            "pending": "⏳",
                            "canceled": "⊘",
                            "skipped": "⊘",
                        }.get(pipeline_status, "?")

                        logger.info(
                            f"MR {mr_id} CI pipeline status: {status_emoji} {pipeline_status}"
                            + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                        )

                        if pipeline_status == "success":
                            pipeline_success = True
                except Exception as e:
                    logger.warning(f"Could not get pipeline status for MR {mr_id}: {e}")

                # Check approval status
                approvals_met = False
                try:
                    approvals = gitlab_client.get_merge_request_approvals(project_id, mr_id)
                    if approvals:
                        approvals_required = approvals.get("approvals_required", 0)
                        approvals_left = approvals.get("approvals_left", 0)
                        approved_by = approvals.get("approved_by", [])

                        if approvals_required > 0:
                            if approvals_left == 0:
                                logger.info(f"MR {mr_id} approval status: ✓ Approved ({len(approved_by)}/{approvals_required} approvals)")
                                approvals_met = True
                            else:
                                logger.info(f"MR {mr_id} approval status: ⏳ Pending ({len(approved_by)}/{approvals_required} approvals, {approvals_left} remaining)")
                        else:
                            logger.info(f"MR {mr_id} approval status: ✓ No approvals required")
                            approvals_met = True
                    else:
                        logger.debug(f"MR {mr_id} approval status: Could not retrieve approval information")
                except Exception as e:
                    logger.warning(f"Could not get approval status for MR {mr_id}: {e}")

                # Try to merge the MR if all requirements are met
                if pipeline_success and approvals_met:
                    try:
                        # Get MR details to check if it can be merged
                        mr_details = gitlab_client.get_merge_request(project_id, mr_id)
                        merge_status = mr_details.get("merge_status", "unknown")
                        detailed_merge_status = mr_details.get("detailed_merge_status", "unknown")
                        can_merge = mr_details.get("user", {}).get("can_merge", False)
                        mr_state = mr_details.get("state", "unknown")
                        has_conflicts = mr_details.get("has_conflicts", False)
                        blocking_discussions_resolved = mr_details.get("blocking_discussions_resolved", True)
                        squash_on_merge = mr_details.get("squash_on_merge", False)

                        # Don't try to merge if already merged or closed
                        if mr_state in ("merged", "closed"):
                            logger.debug(f"MR {mr_id} is already {mr_state}, skipping merge attempt")
                        elif has_conflicts:
                            logger.warning(f"MR {mr_id} has merge conflicts, cannot merge")
                        elif not blocking_discussions_resolved:
                            logger.warning(f"MR {mr_id} has unresolved blocking discussions, cannot merge")
                        elif detailed_merge_status not in ("mergeable", "ci_still_running") and detailed_merge_status != "unknown":
                            # detailed_merge_status can be: "mergeable", "checking", "ci_still_running", "not_approved", etc.
                            logger.debug(f"MR {mr_id} detailed_merge_status is '{detailed_merge_status}', may not be ready to merge")
                        elif merge_status == "can_be_merged" or can_merge:
                            logger.info(f"MR {mr_id} is ready to merge (pipeline: success, approvals: met, merge_status: {merge_status}, detailed_status: {detailed_merge_status})")
                            # If detailed_merge_status indicates checking or not ready, wait a moment for GitLab to update
                            if detailed_merge_status in ("checking", "ci_still_running"):
                                import time
                                logger.debug("Waiting 2 seconds for GitLab to update merge status...")
                                time.sleep(2)
                                # Re-fetch MR to get updated status
                                mr_details = gitlab_client.get_merge_request(project_id, mr_id)
                                detailed_merge_status = mr_details.get("detailed_merge_status", detailed_merge_status)
                                logger.debug(f"MR {mr_id} updated detailed_merge_status: {detailed_merge_status}")

                            # Proactively rebase if needed before merge attempt
                            should_be_rebased = mr_details.get("should_be_rebased", False)
                            if should_be_rebased:
                                logger.info(f"Rebasing MR {mr_id} to ensure it's up-to-date with target branch...")
                                try:
                                    import time
                                    rebase_result = gitlab_client.rebase_merge_request(project_id, mr_id)
                                    logger.debug(f"Rebase result: {rebase_result}")

                                    # Wait for rebase to complete
                                    for _ in range(30):  # Wait up to 60 seconds
                                        time.sleep(2)
                                        mr_check = gitlab_client.get_merge_request(project_id, mr_id)
                                        if not mr_check.get("rebase_in_progress", False):
                                            break
                                        logger.debug("Rebase in progress, waiting...")

                                    # Wait for MR to become mergeable after rebase (CI must pass)
                                    max_wait_seconds = mr_pipeline_timeout
                                    poll_interval = 30
                                    waited = 0
                                    pipeline_url_logged = False

                                    while waited < max_wait_seconds:
                                        mr_details = gitlab_client.get_merge_request(project_id, mr_id)
                                        detailed_merge_status = mr_details.get("detailed_merge_status", "unknown")
                                        logger.debug(f"MR status after rebase: detailed_merge_status={detailed_merge_status} (waited {waited}s)")

                                        if detailed_merge_status == "mergeable":
                                            logger.info(f"MR {mr_id} is mergeable after rebase")
                                            break

                                        if detailed_merge_status in ("approvals_syncing", "checking", "ci_still_running", "ci_must_pass"):
                                            if not pipeline_url_logged:
                                                try:
                                                    pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
                                                    if pipelines:
                                                        latest_pl = pipelines[0]
                                                        pl_web_url = latest_pl.get("web_url", "")
                                                        pl_status = latest_pl.get("status", "unknown")
                                                        logger.info(
                                                            f"Waiting for post-rebase CI pipeline on MR {mr_id} "
                                                            f"(status: {pl_status}, up to {max_wait_seconds // 60} min)"
                                                            + (f" ({pl_web_url})" if pl_web_url else "")
                                                        )
                                                        pipeline_url_logged = True
                                                except Exception:
                                                    pass

                                            time.sleep(poll_interval)
                                            waited += poll_interval
                                            if waited % 300 == 0:
                                                logger.info(f"Still waiting for post-rebase CI on MR {mr_id}... ({waited // 60} min elapsed)")
                                        elif detailed_merge_status in ("not_approved", "blocked_status", "not_open"):
                                            logger.warning(f"MR {mr_id} cannot be merged after rebase: {detailed_merge_status}")
                                            break
                                        else:
                                            time.sleep(poll_interval)
                                            waited += poll_interval

                                    if detailed_merge_status != "mergeable":
                                        logger.warning(
                                            f"MR {mr_id} not mergeable after rebase wait: {detailed_merge_status}. "
                                            f"Manual intervention may be required."
                                        )
                                        # Don't proceed with merge attempt
                                        raise Exception(f"MR not mergeable after rebase: {detailed_merge_status}")
                                except Exception as e:
                                    if "MR not mergeable after rebase" in str(e):
                                        raise
                                    logger.warning(f"Failed to proactively rebase MR {mr_id}: {e}")
                                    # Continue with merge attempt anyway - it might still work

                            try:
                                # Try merging - include squash if project requires it
                                merge_result = gitlab_client.merge_merge_request(
                                    project_id, mr_id, squash=squash_on_merge
                                )
                                if merge_result.get("state") == "merged":
                                    logger.info(f"✓ Successfully merged MR {mr_id}")

                                    # Handle post-merge pipeline
                                    target_branch = mr_details.get("target_branch", "main")
                                    pipeline_ok = True

                                    if wait_for_post_merge_pipeline:
                                        # Wait for post-merge pipeline to complete before generating RPAs
                                        import time
                                        time.sleep(3)  # Wait a moment for pipeline to be triggered
                                        logger.info(f"Waiting for post-merge pipeline on {target_branch} to complete...")
                                        pipeline_ok, pipeline_status, pipeline_url = wait_for_pipeline(
                                            gitlab_client,
                                            project_id,
                                            target_branch,
                                            timeout_seconds=post_merge_pipeline_timeout,
                                        )
                                        if not pipeline_ok:
                                            logger.warning(
                                                f"Post-merge pipeline did not succeed (status: {pipeline_status}). "
                                                f"Proceeding with RPA generation anyway, but konflux CI may fail."
                                            )
                                    else:
                                        # Just check and log the current status (non-blocking)
                                        import time
                                        time.sleep(2)  # Wait a moment for pipeline to be triggered
                                        try:
                                            branch_pipelines = gitlab_client.get_branch_pipelines(project_id, target_branch, limit=3)
                                            if branch_pipelines:
                                                latest_pipeline = branch_pipelines[0]
                                                pipeline_status = latest_pipeline.get("status", "unknown")
                                                pipeline_web_url = latest_pipeline.get("web_url", "")
                                                pipeline_sha = latest_pipeline.get("sha", "")[:8] if latest_pipeline.get("sha") else ""

                                                status_emoji = {
                                                    "success": "✓",
                                                    "failed": "✗",
                                                    "running": "⟳",
                                                    "pending": "⏳",
                                                    "canceled": "⊘",
                                                    "skipped": "⊘",
                                                }.get(pipeline_status, "?")

                                                logger.info(
                                                    f"Post-merge pipeline on {target_branch} ({pipeline_sha}): {status_emoji} {pipeline_status}"
                                                    + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                                                )
                                            else:
                                                logger.debug(f"No pipelines found on {target_branch} branch after merge")
                                        except Exception as e:
                                            logger.debug(f"Could not check post-merge pipeline status: {e}")

                                    # Generate RPAs for all local images (stateless approach)
                                    # The RPA generation is idempotent - it will skip unchanged content
                                    if konflux_repo_path and all_local_images:
                                        merged_image_names = [{"name": img["name"]} for img in all_local_images]
                                        logger.info(f"Generating ReleasePlanAdmissions for {len(merged_image_names)} image(s)...")
                                        try:
                                            generate_and_submit_rpas(
                                                merged_image_names,
                                                mr_id,
                                                gitlab_client,
                                                konflux_repo_path,
                                                pyxis_project_path or "releng/pyxis-repo-configs",
                                                konflux_repo_url,
                                                rpa_config_path,
                                                rpa_template_dir,
                                                dry_run=dry_run,
                                                force=force,
                                            )
                                        except Exception as e:
                                            logger.error(f"Error generating RPAs after MR merge: {e}", exc_info=True)
                                else:
                                    logger.warning(f"MR {mr_id} merge request returned state: {merge_result.get('state')}")
                            except Exception as e:
                                # Check error response for more details
                                error_msg = str(e)
                                status_code = None
                                if hasattr(e, "response") and e.response is not None:
                                    status_code = e.response.status_code
                                    try:
                                        error_body = e.response.text
                                        logger.debug(f"MR {mr_id} merge error response: {error_body}")
                                        if status_code == 401:
                                            logger.warning(
                                                f"Could not merge MR {mr_id}: GitLab token lacks permission to merge MRs (HTTP 401). "
                                                f"Please ensure your token has 'api' scope with 'write_repository' permission. "
                                                f"You may need to merge manually in the GitLab UI: {mr_details.get('web_url', '')}"
                                            )
                                            # Check if MR is already merged (might have been merged manually)
                                            try:
                                                updated_mr = gitlab_client.get_merge_request(project_id, mr_id)
                                                if updated_mr.get("state") == "merged":
                                                    logger.info(f"MR {mr_id} is already merged, proceeding with RPA generation")
                                                    # Generate RPAs for all local images (stateless approach)
                                                    if konflux_repo_path and all_local_images:
                                                        merged_image_names = [{"name": img["name"]} for img in all_local_images]
                                                        logger.info(f"Generating ReleasePlanAdmissions for {len(merged_image_names)} image(s)...")
                                                        try:
                                                            generate_and_submit_rpas(
                                                                merged_image_names,
                                                                mr_id,
                                                                gitlab_client,
                                                                konflux_repo_path,
                                                                pyxis_project_path or "releng/pyxis-repo-configs",
                                                                konflux_repo_url,
                                                                rpa_config_path,
                                                                rpa_template_dir,
                                                                dry_run=dry_run,
                                                                force=force,
                                                            )
                                                        except Exception as e_rpa:
                                                            logger.error(f"Error generating RPAs after MR merge: {e_rpa}", exc_info=True)
                                            except Exception:
                                                pass  # If we can't check, just continue
                                        elif "Branch cannot be merged" in error_body or "cannot be merged" in error_body:
                                            # Try with merge_when_pipeline_succeeds parameter as a workaround
                                            logger.debug("Trying merge with merge_when_pipeline_succeeds parameter as workaround...")
                                            try:
                                                merge_result = gitlab_client.merge_merge_request(
                                                    project_id, mr_id,
                                                    squash=squash_on_merge,
                                                    merge_when_pipeline_succeeds=True
                                                )
                                                if merge_result.get("state") == "merged":
                                                    logger.info(f"✓ Successfully merged MR {mr_id} (with merge_when_pipeline_succeeds)")

                                                    # Handle post-merge pipeline
                                                    target_branch = mr_details.get("target_branch", "main")
                                                    pipeline_ok = True

                                                    if wait_for_post_merge_pipeline:
                                                        # Wait for post-merge pipeline to complete before generating RPAs
                                                        import time
                                                        time.sleep(3)  # Wait a moment for pipeline to be triggered
                                                        logger.info(f"Waiting for post-merge pipeline on {target_branch} to complete...")
                                                        pipeline_ok, pipeline_status, pipeline_url = wait_for_pipeline(
                                                            gitlab_client,
                                                            project_id,
                                                            target_branch,
                                                            timeout_seconds=post_merge_pipeline_timeout,
                                                        )
                                                        if not pipeline_ok:
                                                            logger.warning(
                                                                f"Post-merge pipeline did not succeed (status: {pipeline_status}). "
                                                                f"Proceeding with RPA generation anyway, but konflux CI may fail."
                                                            )
                                                    else:
                                                        # Just check and log the current status (non-blocking)
                                                        import time
                                                        time.sleep(2)  # Wait a moment for pipeline to be triggered
                                                        try:
                                                            branch_pipelines = gitlab_client.get_branch_pipelines(project_id, target_branch, limit=3)
                                                            if branch_pipelines:
                                                                latest_pipeline = branch_pipelines[0]
                                                                pipeline_status = latest_pipeline.get("status", "unknown")
                                                                pipeline_web_url = latest_pipeline.get("web_url", "")
                                                                pipeline_sha = latest_pipeline.get("sha", "")[:8] if latest_pipeline.get("sha") else ""

                                                                status_emoji = {
                                                                    "success": "✓",
                                                                    "failed": "✗",
                                                                    "running": "⟳",
                                                                    "pending": "⏳",
                                                                    "canceled": "⊘",
                                                                    "skipped": "⊘",
                                                                }.get(pipeline_status, "?")

                                                                logger.info(
                                                                    f"Post-merge pipeline on {target_branch} ({pipeline_sha}): {status_emoji} {pipeline_status}"
                                                                    + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                                                                )
                                                            else:
                                                                logger.debug(f"No pipelines found on {target_branch} branch after merge")
                                                        except Exception as e:
                                                            logger.debug(f"Could not check post-merge pipeline status: {e}")

                                                    # Generate RPAs for all local images (stateless approach)
                                                    if konflux_repo_path and all_local_images:
                                                        merged_image_names = [{"name": img["name"]} for img in all_local_images]
                                                        logger.info(f"Generating ReleasePlanAdmissions for {len(merged_image_names)} image(s)...")
                                                        try:
                                                            generate_and_submit_rpas(
                                                                merged_image_names,
                                                                mr_id,
                                                                gitlab_client,
                                                                konflux_repo_path,
                                                                pyxis_project_path or "releng/pyxis-repo-configs",
                                                                konflux_repo_url,
                                                                rpa_config_path,
                                                                rpa_template_dir,
                                                                dry_run=dry_run,
                                                                force=force,
                                                            )
                                                        except Exception as e:
                                                            logger.error(f"Error generating RPAs after MR merge: {e}", exc_info=True)
                                                else:
                                                    logger.warning(
                                                        f"MR {mr_id} cannot be merged via API despite merge_status='can_be_merged'. "
                                                        f"This may be due to GitLab's internal merge checks. Detailed status: {detailed_merge_status}. "
                                                        f"Please merge manually in the GitLab UI."
                                                    )
                                            except Exception as e2:
                                                logger.warning(
                                                    f"MR {mr_id} cannot be merged via API despite merge_status='can_be_merged'. "
                                                    f"This may be due to GitLab's internal merge checks. Detailed status: {detailed_merge_status}. "
                                                    f"Error: {e2}. Please merge manually in the GitLab UI."
                                                )
                                        elif status_code == 405 or status_code == 406:
                                            logger.info(f"MR {mr_id} may already be merged or cannot be merged via API")
                                        else:
                                            logger.warning(f"Could not merge MR {mr_id} (HTTP {status_code}): {error_body}")
                                    except Exception:
                                        if status_code == 401:
                                            logger.warning(
                                                f"Could not merge MR {mr_id}: GitLab token lacks permission to merge MRs (HTTP 401). "
                                                f"Please ensure your token has 'api' scope with 'write_repository' permission."
                                            )
                                        else:
                                            logger.warning(f"Could not merge MR {mr_id} (HTTP {status_code}): {error_msg}")
                                else:
                                    logger.warning(f"Could not merge MR {mr_id}: {error_msg}")
                        else:
                            logger.debug(f"MR {mr_id} cannot be merged yet (merge_status: {merge_status}, detailed_status: {detailed_merge_status}, can_merge: {can_merge})")
                    except Exception as e:
                        logger.warning(f"Could not check merge status or merge MR {mr_id}: {e}")

                # Fail if pipeline has failed (check after merge attempt)
                if not pipeline_success:
                    try:
                        pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
                        if pipelines:
                            latest_pipeline = pipelines[0]
                            pipeline_status = latest_pipeline.get("status", "unknown")
                            pipeline_web_url = latest_pipeline.get("web_url", "")
                            if pipeline_status == "failed":
                                logger.error(
                                    f"MR {mr_id} CI pipeline has failed. Please fix the issues before continuing. "
                                    + (f"See: {pipeline_web_url}" if pipeline_web_url else "")
                                )
                                raise RuntimeError(
                                    f"MR {mr_id} CI pipeline failed. Fix the issues in the pipeline before continuing."
                                )
                    except RuntimeError:
                        raise
                    except Exception as e:
                        logger.debug(f"Could not check pipeline status for failure: {e}")
        return

    # Create branch if it doesn't exist
    if not branch_exists:
        try:
            gitlab_client.create_branch(project_id, branch_name)
            logger.info(f"Created branch {branch_name} from main")
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 400:
                # Branch might have been created between check and create, or already exists
                logger.info(f"Branch {branch_name} already exists, will update it")
                branch_exists = True
            else:
                raise
    elif not has_open_mr:
        # Branch exists but MR was closed, delete and recreate from main to avoid conflicts
        logger.info(
            f"Branch {branch_name} exists but has no open MR (was closed). "
            f"Deleting and recreating from main to ensure clean state..."
        )
        try:
            gitlab_client.delete_branch(project_id, branch_name)
            logger.info(f"Deleted old branch {branch_name}")
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 404:
                # Branch might have been deleted already, that's fine
                logger.debug(f"Branch {branch_name} was already deleted")
            else:
                logger.warning(f"Failed to delete branch {branch_name}: {e}, will try to create anyway")
        # Create fresh branch from main
        try:
            gitlab_client.create_branch(project_id, branch_name, ref="main")
            logger.info(f"Created fresh branch {branch_name} from main")
            branch_exists = True
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 400:
                # Branch might still exist or was recreated, that's fine
                logger.info(f"Branch {branch_name} exists, will use it")
                branch_exists = True
            else:
                raise

    # Update file
    commit_parts = []
    if added_images:
        image_list = ", ".join([f"{img['name']} ({img['repository']})" for img in added_images])
        commit_parts.append(f"Add {len(added_images)} image(s): {image_list}")
    if removed_images:
        image_list = ", ".join([f"{img['name']} ({img['repository']})" for img in removed_images])
        commit_parts.append(f"Remove {len(removed_images)} image(s): {image_list}")
    if content_changed and not added_images and not removed_images:
        commit_parts.append("Update YAML format/structure (e.g., use merge keys for deduplication)")

    commit_message = "chore: Update hummingbird-tech-preview repository list\n\n" + "\n".join(commit_parts)
    # Check if MR exists before updating (to detect if we're updating an existing MR)
    existing_mrs_before_update = gitlab_client.list_merge_requests(
        project_id,
        state="opened",
        source_branch=branch_name,
    )
    mr_exists_before_update = bool(existing_mrs_before_update)

    # Get timestamp of latest pipeline before update (if MR exists)
    latest_pipeline_before_update = None
    if mr_exists_before_update:
        try:
            mr_id_before = existing_mrs_before_update[0]["iid"]
            pipelines_before = gitlab_client.get_merge_request_pipelines(project_id, mr_id_before)
            if pipelines_before:
                latest_pipeline_before_update = pipelines_before[0].get("created_at")
        except Exception:
            # If we can't get pipeline info, that's okay - we'll just wait for new one
            pass

    gitlab_client.create_or_update_file(
        project_id,
        pyxis_file_path,
        updated_content,
        branch_name,
        commit_message,
    )

    # If we updated an existing MR, wait a bit for the new pipeline to be triggered
    if mr_exists_before_update:
        import time
        logger.info("Waiting for new CI pipeline to be triggered after MR update...")
        time.sleep(3)  # Wait 3 seconds for GitLab to trigger new pipeline

    # Check if MR already exists (we need this info to build the title correctly)
    existing_mrs = gitlab_client.list_merge_requests(
        project_id,
        state="opened",
        source_branch=branch_name,
    )

    # Build description and title
    # If MR exists, we need to merge with existing description to preserve history
    existing_added = []
    existing_removed = []
    existing_updated_display = []
    existing_format_update = False

    if existing_mrs:
        mr = existing_mrs[0]
        existing_description = mr.get("description", "")
        if existing_description:
            # Parse existing description to extract sections
            lines = existing_description.split("\n")
            current_section = None
            for line in lines:
                if line.startswith("**Added"):
                    current_section = "added"
                elif line.startswith("**Removed"):
                    current_section = "removed"
                elif line.startswith("**Updated Display Data"):
                    current_section = "updated_display"
                elif line.startswith("**Format Update"):
                    existing_format_update = True
                    current_section = None
                elif line.startswith("Generated by:"):
                    current_section = None
                elif current_section == "added" and line.startswith("- "):
                    existing_added.append(line[2:])  # Remove "- " prefix
                elif current_section == "removed" and line.startswith("- "):
                    existing_removed.append(line[2:])  # Remove "- " prefix
                elif current_section == "updated_display" and line.startswith("- "):
                    existing_updated_display.append(line[2:])  # Remove "- " prefix
                elif current_section and line.strip() == "":
                    # Blank line within a section - continue (don't reset section)
                    continue
                elif current_section and line.strip() and not line.startswith("- "):
                    # Non-list item in a section - might be end of section, but don't reset yet
                    # Only reset if we see a new section header
                    continue

    # Merge added images (combine existing with new)
    all_added = set(existing_added)
    for img in added_images:
        all_added.add(f"{img['name']} ({img['repository']})")

    # Merge removed images (combine existing with new)
    all_removed = set(existing_removed)
    for img in removed_images:
        all_removed.add(f"{img['name']} ({img['repository']})")

    # Merge updated display data
    display_updates_dict: dict[str, set[str]] = {}
    # Parse existing display updates - extract image names as a set
    for item in existing_updated_display:
        if ": now includes " in item:
            repo, names_part = item.split(": now includes ", 1)
            # Parse the comma-separated list of image names
            existing_names = [name.strip() for name in names_part.split(",") if name.strip()]
            # Clean up any trailing "s" that might be a result of the previous bug
            # (where " images" was incorrectly parsed, leaving just "s")
            # Pattern: names ending with a digit followed by "s" (e.g., "aspnet-runtime-9-0s")
            cleaned_names = []
            for name in existing_names:
                if name.endswith("s") and len(name) > 1 and name[-2].isdigit():
                    # Likely a bug artifact - remove the trailing "s"
                    cleaned_names.append(name[:-1])
                else:
                    cleaned_names.append(name)
            display_updates_dict[repo] = set(cleaned_names)
    # Add/update with new display data changes
    for update in updated_display_data:
        # Get existing names for this repo, or create new set
        repo_names = display_updates_dict.get(update['repository'], set())
        # Add new image names to the set (automatically handles duplicates)
        repo_names.update(update['image_names'])
        display_updates_dict[update['repository']] = repo_names

    # Build title based on merged data
    changes_summary = []
    if all_added:
        changes_summary.append(f"Adds {len(all_added)} image(s)")
    if all_removed:
        changes_summary.append(f"Removes {len(all_removed)} image(s)")
    if display_updates_dict:
        changes_summary.append(f"Updates {len(display_updates_dict)} display data entry(ies)")
    if (existing_format_update or (content_changed and not added_images and not removed_images and not updated_display_data)) and not changes_summary:
        changes_summary.append("Updates YAML format/structure")

    # Build title - use simple format if only one type of change and it's a new MR
    if not existing_mrs and len(all_added) == 1 and not all_removed and not display_updates_dict:
        mr_title = f"chore: Onboard {list(all_added)[0].split(' (')[0]} image to hummingbird-tech-preview"
    elif not existing_mrs and len(all_removed) == 1 and not all_added and not display_updates_dict:
        mr_title = f"chore: Remove {list(all_removed)[0].split(' (')[0]} image from hummingbird-tech-preview"
    else:
        mr_title = f"chore: Update hummingbird-tech-preview repository list ({', '.join(changes_summary)})"

    # Build description with merged data
    mr_description = "Updates the hummingbird-tech-preview repository list:\n\n"
    if all_added:
        mr_description += f"**Added ({len(all_added)}):**\n"
        for item in sorted(all_added):
            mr_description += f"- {item}\n"
        mr_description += "\n"
    if all_removed:
        mr_description += f"**Removed ({len(all_removed)}):**\n"
        for item in sorted(all_removed):
            mr_description += f"- {item}\n"
        mr_description += "\n"
    if display_updates_dict:
        mr_description += f"**Updated Display Data ({len(display_updates_dict)}):**\n"
        for repo in sorted(display_updates_dict.keys()):
            # display_updates_dict[repo] is a set, so we need to sort and join
            names_list = sorted(display_updates_dict[repo])
            names_str = ", ".join(names_list)
            mr_description += f"- {repo}: now includes {names_str}\n"
        mr_description += "\n"
    if (existing_format_update or (content_changed and not added_images and not removed_images and not updated_display_data)) and not all_added and not all_removed and not display_updates_dict:
        mr_description += "**Format Update:**\n"
        mr_description += "- Updated YAML structure (e.g., using merge keys for deduplication)\n\n"
    mr_description += "Generated by: ci/onboard_components_to_releng.py"

    if existing_mrs:
        mr = existing_mrs[0]
        mr_id = mr["iid"]
        logger.info(f"MR {mr_id} already exists, updated with new images")

        # Update MR description, title, and ensure auto-merge is enabled
        if added_images or removed_images or updated_display_data or (content_changed and not added_images and not removed_images and not updated_display_data):
            try:
                gitlab_client.update_merge_request(
                    project_id,
                    mr_id,
                    title=mr_title,
                    description=mr_description,
                    merge_when_pipeline_succeeds=True,
                )
                logger.info(f"Updated MR {mr_id} description, title, and enabled auto-merge")
            except Exception as e:
                logger.warning(f"Failed to update MR {mr_id} description: {e}")
        else:
            # Even if no content changes, ensure auto-merge is enabled
            try:
                gitlab_client.update_merge_request(
                    project_id,
                    mr_id,
                    merge_when_pipeline_succeeds=True,
                )
                logger.info(f"Ensured auto-merge is enabled for MR {mr_id}")
            except Exception as e:
                logger.warning(f"Could not update auto-merge setting for MR {mr_id}: {e}")

        # Check CI pipeline status
        # If we updated the MR, only check the new pipeline (created after our update)
        try:
            pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
            if pipelines:
                # Filter to only new pipelines (created after our update) if we updated the MR
                if mr_exists_before_update and latest_pipeline_before_update:
                    new_pipelines = [
                        p for p in pipelines
                        if p.get("created_at", "") > latest_pipeline_before_update
                    ]
                    if new_pipelines:
                        # Use the newest pipeline from after our update
                        latest_pipeline = new_pipelines[0]
                        logger.debug("Found new pipeline created after MR update")
                    else:
                        # No new pipeline yet, wait a bit more and check again
                        import time
                        logger.info("Waiting for new CI pipeline to appear...")
                        time.sleep(5)
                        pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
                        new_pipelines = [
                            p for p in pipelines
                            if p.get("created_at", "") > latest_pipeline_before_update
                        ]
                        if new_pipelines:
                            latest_pipeline = new_pipelines[0]
                            logger.debug("Found new pipeline after additional wait")
                        else:
                            # Still no new pipeline, use the latest one but don't fail on old status
                            latest_pipeline = pipelines[0]
                            logger.info(
                                "New pipeline not yet visible, checking latest pipeline "
                                "(may be from before update)"
                            )
                else:
                    # MR was just created or we couldn't get before timestamp, use latest
                    latest_pipeline = pipelines[0]

                pipeline_status = latest_pipeline.get("status", "unknown")
                pipeline_web_url = latest_pipeline.get("web_url", "")

                status_emoji = {
                    "success": "✓",
                    "failed": "✗",
                    "running": "⟳",
                    "pending": "⏳",
                    "canceled": "⊘",
                    "skipped": "⊘",
                }.get(pipeline_status, "?")

                logger.info(
                    f"MR {mr_id} CI pipeline status: {status_emoji} {pipeline_status}"
                    + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                )

                # Check approval status
                try:
                    approvals = gitlab_client.get_merge_request_approvals(project_id, mr_id)
                    if approvals:
                        approvals_required = approvals.get("approvals_required", 0)
                        approvals_left = approvals.get("approvals_left", 0)
                        approved_by = approvals.get("approved_by", [])

                        if approvals_required > 0:
                            if approvals_left == 0:
                                logger.info(f"MR {mr_id} approval status: ✓ Approved ({len(approved_by)}/{approvals_required} approvals)")
                            else:
                                logger.info(f"MR {mr_id} approval status: ⏳ Pending ({len(approved_by)}/{approvals_required} approvals, {approvals_left} remaining)")
                        else:
                            logger.info(f"MR {mr_id} approval status: No approvals required")
                    else:
                        logger.debug(f"MR {mr_id} approval status: Could not retrieve approval information")
                except Exception as e:
                    logger.warning(f"Could not get approval status for MR {mr_id}: {e}")

                # Only fail if this is a new pipeline (created after our update) and it failed
                # If it's an old pipeline, we don't want to fail since a new one will be triggered
                is_new_pipeline = (
                    not mr_exists_before_update or
                    not latest_pipeline_before_update or
                    latest_pipeline.get("created_at", "") > latest_pipeline_before_update
                )

                if pipeline_status == "failed" and is_new_pipeline:
                    logger.error(
                        f"MR {mr_id} CI pipeline has failed. Please fix the issues before continuing. "
                        + (f"See: {pipeline_web_url}" if pipeline_web_url else "")
                    )
                    raise RuntimeError(
                        f"MR {mr_id} CI pipeline failed. Fix the issues in the pipeline before continuing."
                    )
                elif pipeline_status == "failed" and not is_new_pipeline:
                    logger.info(
                        f"MR {mr_id} old CI pipeline failed, but new pipeline should be triggered. "
                        f"Not failing on old pipeline status."
                    )

                # If pipeline is still running/pending and waiting is enabled, wait for it to finish
                if wait_for_mr_pipeline and pipeline_status in ("running", "pending", "created"):
                    import time
                    poll_interval = 30
                    waited = 0
                    logger.info(
                        f"Waiting for CI pipeline to finish on MR {mr_id} "
                        f"(up to {mr_pipeline_timeout // 60} min)"
                        + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                    )
                    while pipeline_status in ("running", "pending", "created") and waited < mr_pipeline_timeout:
                        time.sleep(poll_interval)
                        waited += poll_interval
                        try:
                            pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
                            if pipelines:
                                latest_pipeline = pipelines[0]
                                pipeline_status = latest_pipeline.get("status", "unknown")
                                pipeline_web_url = latest_pipeline.get("web_url", pipeline_web_url)
                        except Exception:
                            pass
                        if waited % 300 == 0:
                            logger.info(
                                f"Still waiting for CI pipeline on MR {mr_id}... "
                                f"({waited // 60} min elapsed, status: {pipeline_status})"
                            )

                    # Log final pipeline status after waiting
                    final_emoji = {
                        "success": "✓", "failed": "✗", "running": "⟳",
                        "pending": "⏳", "canceled": "⊘", "skipped": "⊘",
                    }.get(pipeline_status, "?")
                    if waited > 0:
                        logger.info(
                            f"MR {mr_id} CI pipeline result after {waited // 60} min: "
                            f"{final_emoji} {pipeline_status}"
                            + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                        )

                    if pipeline_status == "failed":
                        logger.error(
                            f"MR {mr_id} CI pipeline has failed. Please fix the issues before continuing. "
                            + (f"See: {pipeline_web_url}" if pipeline_web_url else "")
                        )
                        raise RuntimeError(
                            f"MR {mr_id} CI pipeline failed. Fix the issues in the pipeline before continuing."
                        )

                    # If pipeline succeeded, wait for auto-merge to complete and generate RPAs
                    if pipeline_status == "success":
                        # Check and attempt approval before waiting for merge
                        approvals_met = False
                        try:
                            approvals = gitlab_client.get_merge_request_approvals(project_id, mr_id)
                            if approvals:
                                approvals_required = approvals.get("approvals_required", 0)
                                approvals_left = approvals.get("approvals_left", 0)
                                approved_by = approvals.get("approved_by", [])

                                if approvals_required > 0:
                                    if approvals_left == 0:
                                        logger.info(f"MR {mr_id} approval status: ✓ Approved ({len(approved_by)}/{approvals_required} approvals)")
                                        approvals_met = True
                                    else:
                                        logger.info(f"MR {mr_id} approval status: ⏳ Pending ({len(approved_by)}/{approvals_required} approvals, {approvals_left} remaining)")

                                        # Attempt to approve via API
                                        logger.info(f"Attempting to approve MR {mr_id} via API...")
                                        try:
                                            approve_result = gitlab_client.approve_merge_request(project_id, mr_id)
                                            if approve_result:
                                                logger.info(f"✓ Successfully approved MR {mr_id}")
                                                approvals_met = True
                                            else:
                                                logger.info(
                                                    f"Could not approve MR {mr_id} via API "
                                                    "(may require manual approval in GitLab UI)"
                                                )
                                        except Exception as e:
                                            logger.debug(f"Approval attempt failed for MR {mr_id}: {e}")
                                            logger.info(
                                                f"Could not approve MR {mr_id} via API "
                                                "(may require manual approval in GitLab UI)"
                                            )
                                else:
                                    logger.info(f"MR {mr_id} approval status: No approvals required")
                                    approvals_met = True
                            else:
                                approvals_met = True
                        except Exception as e:
                            logger.warning(f"Could not get approval status for MR {mr_id}: {e}")
                            approvals_met = True  # Assume no approvals required if we can't check

                        # If approvals are met, attempt to merge directly
                        mr_merged = False
                        if approvals_met:
                            try:
                                mr_details = gitlab_client.get_merge_request(project_id, mr_id)
                                detailed_merge_status = mr_details.get("detailed_merge_status", "unknown")
                                if detailed_merge_status == "mergeable":
                                    logger.info(f"MR {mr_id} is mergeable, attempting to merge...")
                                    try:
                                        merge_result = gitlab_client.merge_merge_request(project_id, mr_id, squash=True)
                                        if merge_result.get("state") == "merged":
                                            mr_merged = True
                                            logger.info(f"✓ MR {mr_id} has been merged")
                                    except Exception as e:
                                        logger.debug(f"Merge attempt failed for MR {mr_id}: {e}")
                                        logger.info(f"Could not merge MR {mr_id} via API, will wait for auto-merge")
                                else:
                                    logger.debug(f"MR {mr_id} detailed_merge_status is '{detailed_merge_status}', waiting for it to become mergeable")
                            except Exception as e:
                                logger.debug(f"Could not check MR {mr_id} merge status: {e}")

                        # If not merged yet, wait for auto-merge or manual merge
                        if not mr_merged:
                            logger.info(f"Waiting for MR {mr_id} to be merged...")
                            merge_wait_start = time.time()
                            merge_timeout = 3600  # Wait up to 1 hour
                            
                            while time.time() - merge_wait_start < merge_timeout:
                                try:
                                    mr_details = gitlab_client.get_merge_request(project_id, mr_id)
                                    mr_state = mr_details.get("state", "unknown")
                                    if mr_state == "merged":
                                        mr_merged = True
                                        logger.info(f"MR {mr_id} has been merged")
                                        break
                                    elif mr_state != "opened":
                                        logger.warning(f"MR {mr_id} is in unexpected state: {mr_state}")
                                        break
                                    
                                    # Try to merge if it becomes mergeable
                                    detailed_merge_status = mr_details.get("detailed_merge_status", "unknown")
                                    if detailed_merge_status == "mergeable":
                                        try:
                                            merge_result = gitlab_client.merge_merge_request(project_id, mr_id, squash=True)
                                            if merge_result.get("state") == "merged":
                                                mr_merged = True
                                                logger.info(f"✓ MR {mr_id} has been merged")
                                                break
                                        except Exception:
                                            pass  # Will retry on next iteration
                                except Exception as e:
                                    logger.debug(f"Error checking MR state: {e}")
                                time.sleep(5)

                        if mr_merged:
                            # MR was merged, now we should generate RPAs
                            # This will be handled by the next run of the script or by the konflux-release-data flow
                            logger.info(
                                f"MR {mr_id} merged successfully. "
                                "RPAs will be generated in the next phase if --konflux-release-data-repo-path is set."
                            )
                        else:
                            logger.info(
                                f"MR {mr_id} not yet merged (may need manual approval or have merge conflicts). "
                                f"Check: https://gitlab.cee.redhat.com/releng/pyxis-repo-configs/-/merge_requests/{mr_id}"
                            )
            else:
                logger.info(f"MR {mr_id} has no CI pipelines")
        except RuntimeError:
            # Re-raise RuntimeError (pipeline failed)
            raise
        except Exception as e:
            logger.debug(f"Could not get pipeline status for MR {mr_id}: {e}")
    else:
        mr = gitlab_client.create_merge_request(
            project_id,
            branch_name,
            "main",
            mr_title,
            mr_description,
            merge_when_pipeline_succeeds=True,
        )
        mr_id = mr["iid"]
        logger.info(f"Created MR {mr_id} for {len(added_images)} image(s) (auto-merge enabled)")

        # Wait for CI pipeline to be triggered after MR creation
        import time
        logger.info("Waiting for CI pipeline to be triggered after MR creation...")
        time.sleep(3)  # Wait 3 seconds for GitLab to trigger pipeline

        # Check for new pipeline
        try:
            pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
            if not pipelines:
                # No pipeline yet, wait a bit more and check again
                logger.info("No pipeline visible yet, waiting additional time...")
                time.sleep(5)
                pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)

            if pipelines:
                latest_pipeline = pipelines[0]
                pipeline_status = latest_pipeline.get("status", "unknown")
                pipeline_web_url = latest_pipeline.get("web_url", "")
                pipeline_sha = latest_pipeline.get("sha", "")[:8] if latest_pipeline.get("sha") else ""

                status_emoji = {
                    "success": "✓",
                    "failed": "✗",
                    "running": "⟳",
                    "pending": "⏳",
                    "canceled": "⊘",
                    "skipped": "⊘",
                }.get(pipeline_status, "?")

                logger.info(
                    f"MR {mr_id} CI pipeline status: {status_emoji} {pipeline_status}"
                    + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                    + (f" ({pipeline_sha})" if pipeline_sha else "")
                )

                # If pipeline is still running/pending and waiting is enabled, wait for it to finish
                if wait_for_mr_pipeline and pipeline_status in ("running", "pending", "created"):
                    poll_interval = 30
                    waited = 0
                    logger.info(
                        f"Waiting for CI pipeline to finish on MR {mr_id} "
                        f"(up to {mr_pipeline_timeout // 60} min)"
                        + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                    )
                    while pipeline_status in ("running", "pending", "created") and waited < mr_pipeline_timeout:
                        time.sleep(poll_interval)
                        waited += poll_interval
                        try:
                            pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
                            if pipelines:
                                latest_pipeline = pipelines[0]
                                pipeline_status = latest_pipeline.get("status", "unknown")
                                pipeline_web_url = latest_pipeline.get("web_url", pipeline_web_url)
                        except Exception:
                            pass
                        if waited % 300 == 0:
                            logger.info(
                                f"Still waiting for CI pipeline on MR {mr_id}... "
                                f"({waited // 60} min elapsed, status: {pipeline_status})"
                            )

                    # Log final pipeline status after waiting
                    final_emoji = {
                        "success": "✓", "failed": "✗", "running": "⟳",
                        "pending": "⏳", "canceled": "⊘", "skipped": "⊘",
                    }.get(pipeline_status, "?")
                    if waited > 0:
                        logger.info(
                            f"MR {mr_id} CI pipeline result after {waited // 60} min: "
                            f"{final_emoji} {pipeline_status}"
                            + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                        )

                    if pipeline_status == "failed":
                        logger.error(
                            f"MR {mr_id} CI pipeline has failed. Please fix the issues before continuing."
                            + (f" See: {pipeline_web_url}" if pipeline_web_url else "")
                        )
                        raise RuntimeError(
                            f"MR {mr_id} CI pipeline failed. Fix the issues in the pipeline before continuing."
                        )

                    # If pipeline succeeded, wait for auto-merge to complete and generate RPAs
                    if pipeline_status == "success":
                        # Check and attempt approval before waiting for merge
                        approvals_met = False
                        try:
                            approvals = gitlab_client.get_merge_request_approvals(project_id, mr_id)
                            if approvals:
                                approvals_required = approvals.get("approvals_required", 0)
                                approvals_left = approvals.get("approvals_left", 0)
                                approved_by = approvals.get("approved_by", [])

                                if approvals_required > 0:
                                    if approvals_left == 0:
                                        logger.info(f"MR {mr_id} approval status: ✓ Approved ({len(approved_by)}/{approvals_required} approvals)")
                                        approvals_met = True
                                    else:
                                        logger.info(f"MR {mr_id} approval status: ⏳ Pending ({len(approved_by)}/{approvals_required} approvals, {approvals_left} remaining)")

                                        # Attempt to approve via API
                                        logger.info(f"Attempting to approve MR {mr_id} via API...")
                                        try:
                                            approve_result = gitlab_client.approve_merge_request(project_id, mr_id)
                                            if approve_result:
                                                logger.info(f"✓ Successfully approved MR {mr_id}")
                                                approvals_met = True
                                            else:
                                                logger.info(
                                                    f"Could not approve MR {mr_id} via API "
                                                    "(may require manual approval in GitLab UI)"
                                                )
                                        except Exception as e:
                                            logger.debug(f"Approval attempt failed for MR {mr_id}: {e}")
                                            logger.info(
                                                f"Could not approve MR {mr_id} via API "
                                                "(may require manual approval in GitLab UI)"
                                            )
                                else:
                                    logger.info(f"MR {mr_id} approval status: No approvals required")
                                    approvals_met = True
                            else:
                                approvals_met = True
                        except Exception as e:
                            logger.warning(f"Could not get approval status for MR {mr_id}: {e}")
                            approvals_met = True  # Assume no approvals required if we can't check

                        # If approvals are met, attempt to merge directly
                        mr_merged = False
                        if approvals_met:
                            try:
                                mr_details = gitlab_client.get_merge_request(project_id, mr_id)
                                detailed_merge_status = mr_details.get("detailed_merge_status", "unknown")
                                if detailed_merge_status == "mergeable":
                                    logger.info(f"MR {mr_id} is mergeable, attempting to merge...")
                                    try:
                                        merge_result = gitlab_client.merge_merge_request(project_id, mr_id, squash=True)
                                        if merge_result.get("state") == "merged":
                                            mr_merged = True
                                            logger.info(f"✓ MR {mr_id} has been merged")
                                    except Exception as e:
                                        logger.debug(f"Merge attempt failed for MR {mr_id}: {e}")
                                        logger.info(f"Could not merge MR {mr_id} via API, will wait for auto-merge")
                                else:
                                    logger.debug(f"MR {mr_id} detailed_merge_status is '{detailed_merge_status}', waiting for it to become mergeable")
                            except Exception as e:
                                logger.debug(f"Could not check MR {mr_id} merge status: {e}")

                        # If not merged yet, wait for auto-merge or manual merge
                        if not mr_merged:
                            logger.info(f"Waiting for MR {mr_id} to be merged...")
                            merge_wait_start = time.time()
                            merge_timeout = 3600  # Wait up to 1 hour

                            while time.time() - merge_wait_start < merge_timeout:
                                try:
                                    mr_details = gitlab_client.get_merge_request(project_id, mr_id)
                                    mr_state = mr_details.get("state", "unknown")
                                    if mr_state == "merged":
                                        mr_merged = True
                                        logger.info(f"MR {mr_id} has been merged")
                                        break
                                    elif mr_state == "closed":
                                        logger.warning(f"MR {mr_id} was closed without merging")
                                        break

                                    # Try to merge if it becomes mergeable
                                    detailed_merge_status = mr_details.get("detailed_merge_status", "unknown")
                                    if detailed_merge_status == "mergeable":
                                        try:
                                            merge_result = gitlab_client.merge_merge_request(project_id, mr_id, squash=True)
                                            if merge_result.get("state") == "merged":
                                                mr_merged = True
                                                logger.info(f"✓ MR {mr_id} has been merged")
                                                break
                                        except Exception:
                                            pass  # Will retry on next iteration
                                    time.sleep(5)
                                except Exception as e:
                                    logger.debug(f"Error checking MR {mr_id} state: {e}")
                                    time.sleep(5)

                        # Generate RPAs if MR was merged
                        if mr_merged and konflux_repo_path and all_local_images:
                            # Optionally wait for post-merge pipeline
                            if wait_for_post_merge_pipeline:
                                target_branch = mr_details.get("target_branch", "main")
                                logger.info(f"Waiting for post-merge pipeline on {target_branch} branch...")
                                success, status, web_url = wait_for_pipeline(
                                    gitlab_client,
                                    project_id,
                                    target_branch,
                                    timeout_seconds=post_merge_pipeline_timeout,
                                )
                                if not success:
                                    logger.warning(
                                        f"Post-merge pipeline did not succeed (status: {status}). "
                                        f"Proceeding with RPA generation anyway, but konflux CI may fail."
                                    )

                            merged_image_names = [{"name": img["name"]} for img in all_local_images]
                            logger.info(f"Generating ReleasePlanAdmissions for {len(merged_image_names)} image(s)...")
                            try:
                                generate_and_submit_rpas(
                                    merged_image_names,
                                    mr_id,
                                    gitlab_client,
                                    konflux_repo_path,
                                    pyxis_project_path or "releng/pyxis-repo-configs",
                                    konflux_repo_url,
                                    rpa_config_path,
                                    rpa_template_dir,
                                    dry_run=dry_run,
                                    force=force,
                                )
                            except Exception as e:
                                logger.error(f"Error generating RPAs after MR merge: {e}", exc_info=True)
                        elif not mr_merged:
                            logger.info(
                                f"MR {mr_id} auto-merge not yet complete. "
                                f"RPAs will be generated on next run when MR is merged."
                            )
            else:
                logger.debug(f"MR {mr_id} pipeline not yet visible (may start shortly)")
        except RuntimeError:
            raise
        except Exception as e:
            logger.debug(f"Could not check pipeline status for newly created MR {mr_id}: {e}")

    # Final summary
    change_summary = []
    if added_images:
        change_summary.append(f"added {len(added_images)}")
    if removed_images:
        change_summary.append(f"removed {len(removed_images)}")

    summary_msg = "Successfully updated repository list"
    if change_summary:
        summary_msg += f" ({', '.join(change_summary)})"
    summary_msg += f" (MR: {mr_id})"

    if images_to_onboard and len(added_images) < len(images_to_onboard):
        skipped_count = len(images_to_onboard) - len(added_images)
        summary_msg += f"\nNote: {skipped_count} of {len(images_to_onboard)} checked image(s) were skipped because they already exist in the YAML file"

    logger.info(summary_msg)


def wait_for_pipeline(
    gitlab_client: GitLabClient,
    project_id: int,
    branch: str,
    timeout_seconds: int = 600,
    poll_interval: int = 15,
) -> tuple[bool, str, str]:
    """Wait for the latest pipeline on a branch to complete.

    Args:
        gitlab_client: GitLabClient instance
        project_id: GitLab project ID
        branch: Branch name to check pipelines for
        timeout_seconds: Maximum time to wait (default: 600 = 10 minutes)
        poll_interval: Seconds between status checks (default: 15)

    Returns:
        Tuple of (success: bool, status: str, web_url: str)
        success is True if pipeline completed with 'success' status
    """
    import time

    start_time = time.time()
    last_pipeline_id = None

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            logger.warning(f"Timeout waiting for pipeline on {branch} after {timeout_seconds}s")
            return False, "timeout", ""

        try:
            pipelines = gitlab_client.get_branch_pipelines(project_id, branch, limit=3)
            if not pipelines:
                logger.debug(f"No pipelines found on {branch}, waiting...")
                time.sleep(poll_interval)
                continue

            latest_pipeline = pipelines[0]
            pipeline_id = latest_pipeline.get("id")
            pipeline_status = latest_pipeline.get("status", "unknown")
            pipeline_web_url = latest_pipeline.get("web_url", "")
            pipeline_sha = latest_pipeline.get("sha", "")[:8] if latest_pipeline.get("sha") else ""

            # Log status changes
            if pipeline_id != last_pipeline_id:
                last_pipeline_id = pipeline_id
                logger.info(f"Watching pipeline {pipeline_id} on {branch} ({pipeline_sha}): {pipeline_web_url}")

            status_emoji = {
                "success": "✓",
                "failed": "✗",
                "running": "⟳",
                "pending": "⏳",
                "canceled": "⊘",
                "skipped": "⊘",
            }.get(pipeline_status, "?")

            # Check for terminal states
            if pipeline_status == "success":
                logger.info(f"Post-merge pipeline completed: {status_emoji} {pipeline_status}")
                return True, pipeline_status, pipeline_web_url
            elif pipeline_status in ("failed", "canceled", "skipped"):
                logger.warning(f"Post-merge pipeline ended: {status_emoji} {pipeline_status} ({pipeline_web_url})")
                return False, pipeline_status, pipeline_web_url
            else:
                # Still running or pending
                remaining = int(timeout_seconds - elapsed)
                logger.debug(f"Pipeline {pipeline_id} status: {pipeline_status}, waiting... ({remaining}s remaining)")
                time.sleep(poll_interval)

        except Exception as e:
            logger.debug(f"Error checking pipeline status: {e}")
            time.sleep(poll_interval)


def check_existing_mrs(
    gitlab_client: GitLabClient,
    project_id: int,
    pyxis_project_path: str | None = None,
    konflux_repo_path: str | None = None,
    konflux_repo_url: str | None = None,
    rpa_config_path: Path | None = None,
    rpa_template_dir: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    wait_for_post_merge_pipeline: bool = False,
    post_merge_pipeline_timeout: int = 600,
) -> None:
    """Check status of existing merge requests by querying GitLab directly.

    This function is stateless - it queries GitLab for open MRs on the known
    branch name instead of using a tracking file.
    """
    logger.info("Checking status of existing merge requests...")

    # In debug mode, also show merged/closed MRs for history
    if logger.isEnabledFor(logging.DEBUG):
        try:
            merged_mrs = gitlab_client.list_merge_requests(
                project_id,
                state="merged",
                source_branch=PYXIS_BRANCH_NAME,
            )
            if merged_mrs:
                logger.debug(f"Found {len(merged_mrs)} merged MR(s) on branch {PYXIS_BRANCH_NAME}:")
                for mr in merged_mrs[:5]:  # Show up to 5 most recent
                    logger.debug(f"  - MR !{mr['iid']}: {mr.get('title', 'No title')} (merged: {mr.get('merged_at', 'unknown')})")
        except Exception as e:
            logger.debug(f"Could not list merged MRs: {e}")

        try:
            closed_mrs = gitlab_client.list_merge_requests(
                project_id,
                state="closed",
                source_branch=PYXIS_BRANCH_NAME,
            )
            if closed_mrs:
                logger.debug(f"Found {len(closed_mrs)} closed MR(s) on branch {PYXIS_BRANCH_NAME}:")
                for mr in closed_mrs[:5]:  # Show up to 5 most recent
                    logger.debug(f"  - MR !{mr['iid']}: {mr.get('title', 'No title')}")
        except Exception as e:
            logger.debug(f"Could not list closed MRs: {e}")

    # Query GitLab for open MRs on the pyxis onboarding branch
    try:
        open_mrs = gitlab_client.list_merge_requests(
            project_id,
            state="opened",
            source_branch=PYXIS_BRANCH_NAME,
        )
    except Exception as e:
        logger.warning(f"Could not list open MRs: {e}")
        open_mrs = []

    if not open_mrs:
        logger.info(f"No open MRs found on branch {PYXIS_BRANCH_NAME}")
        return

    logger.debug(f"Found {len(open_mrs)} open MR(s) on branch {PYXIS_BRANCH_NAME}")

    # Check each open MR
    for mr in open_mrs:
        mr_id = mr["iid"]
        try:
            # Refresh MR details
            mr = gitlab_client.get_merge_request(project_id, mr_id)
            state = mr.get("state")
            merge_status = mr.get("merge_status", "unknown")

            # Check for merge conflicts
            if merge_status == "cannot_be_merged":
                logger.error(
                    f"MR {mr_id} has merge conflicts and cannot be merged automatically. "
                    f"This usually happens when the target file was updated directly in the main branch. "
                    f"Please resolve conflicts manually in GitLab or rebase the branch."
                )

            # Check CI pipeline status for open MRs
            if state == "opened":
                try:
                    pipelines = gitlab_client.get_merge_request_pipelines(project_id, mr_id)
                    if pipelines:
                        # Get the latest pipeline (pipelines are usually sorted by creation date, newest first)
                        latest_pipeline = pipelines[0]
                        pipeline_status = latest_pipeline.get("status", "unknown")
                        pipeline_web_url = latest_pipeline.get("web_url", "")

                        status_emoji = {
                            "success": "✓",
                            "failed": "✗",
                            "running": "⟳",
                            "pending": "⏳",
                            "canceled": "⊘",
                            "skipped": "⊘",
                        }.get(pipeline_status, "?")

                        logger.info(
                            f"MR {mr_id} CI pipeline status: {status_emoji} {pipeline_status}"
                            + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                        )

                        # Check approval status
                        try:
                            approvals = gitlab_client.get_merge_request_approvals(project_id, mr_id)
                            if approvals:
                                approvals_required = approvals.get("approvals_required", 0)
                                approvals_left = approvals.get("approvals_left", 0)
                                approved_by = approvals.get("approved_by", [])

                                if approvals_required > 0:
                                    if approvals_left == 0:
                                        logger.info(f"MR {mr_id} approval status: ✓ Approved ({len(approved_by)}/{approvals_required} approvals)")
                                    else:
                                        logger.info(f"MR {mr_id} approval status: ⏳ Pending ({len(approved_by)}/{approvals_required} approvals, {approvals_left} remaining)")

                                        # Attempt to approve via API if CI passed
                                        if pipeline_status == "success":
                                            logger.info(f"Attempting to approve MR {mr_id} via API...")
                                            try:
                                                approve_result = gitlab_client.approve_merge_request(project_id, mr_id)
                                                if approve_result:
                                                    logger.info(f"✓ Successfully approved MR {mr_id}")
                                                else:
                                                    logger.info(
                                                        f"Could not approve MR {mr_id} via API "
                                                        "(may require manual approval in GitLab UI)"
                                                    )
                                            except Exception as e:
                                                logger.debug(f"Approval attempt failed for MR {mr_id}: {e}")
                                                logger.info(
                                                    f"Could not approve MR {mr_id} via API "
                                                    "(may require manual approval in GitLab UI)"
                                                )
                                else:
                                    logger.info(f"MR {mr_id} approval status: No approvals required")
                            else:
                                logger.debug(f"MR {mr_id} approval status: Could not retrieve approval information")
                        except Exception as e:
                            logger.warning(f"Could not get approval status for MR {mr_id}: {e}")

                        # Fail if pipeline has failed
                        if pipeline_status == "failed":
                            logger.error(
                                f"MR {mr_id} CI pipeline has failed. Please fix the issues before continuing. "
                                + (f"See: {pipeline_web_url}" if pipeline_web_url else "")
                            )
                            raise RuntimeError(
                                f"MR {mr_id} CI pipeline failed. Fix the issues in the pipeline before continuing."
                            )
                    else:
                        logger.info(f"MR {mr_id} has no CI pipelines")
                        # Check approval status even if no pipelines
                        try:
                            approvals = gitlab_client.get_merge_request_approvals(project_id, mr_id)
                            if approvals:
                                approvals_required = approvals.get("approvals_required", 0)
                                approvals_left = approvals.get("approvals_left", 0)
                                approved_by = approvals.get("approved_by", [])

                                if approvals_required > 0:
                                    if approvals_left == 0:
                                        logger.info(f"MR {mr_id} approval status: ✓ Approved ({len(approved_by)}/{approvals_required} approvals)")
                                    else:
                                        logger.info(f"MR {mr_id} approval status: ⏳ Pending ({len(approved_by)}/{approvals_required} approvals, {approvals_left} remaining)")
                                else:
                                    logger.info(f"MR {mr_id} approval status: No approvals required")
                            else:
                                logger.debug(f"MR {mr_id} approval status: Could not retrieve approval information")
                        except Exception as e:
                            logger.warning(f"Could not get approval status for MR {mr_id}: {e}")
                except RuntimeError:
                    # Re-raise RuntimeError (pipeline failed)
                    raise
                except Exception as e:
                    logger.debug(f"Could not get pipeline status for MR {mr_id}: {e}")

        except Exception as e:
            logger.error(f"Error checking MR {mr_id}: {e}")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Onboard container image components to release engineering repositories",
    )
    parser.add_argument(
        "--gitlab-token",
        default=os.getenv("GITLAB_TOKEN"),
        help="GitLab API token (default: GITLAB_TOKEN env var)",
    )
    parser.add_argument(
        "--gitlab-url",
        default=os.getenv("GITLAB_URL", "https://gitlab.cee.redhat.com"),
        help="GitLab URL (default: GITLAB_URL env var or https://gitlab.cee.redhat.com)",
    )
    parser.add_argument(
        "--pyxis-repo-configs-project-path",
        default="releng/pyxis-repo-configs",
        help="GitLab project path for pyxis-repo-configs repository (default: releng/pyxis-repo-configs)",
    )
    parser.add_argument(
        "--pyxis-file-path",
        default=PYXIS_REPO_PATH,
        help=f"File path within pyxis-repo-configs repository (default: {PYXIS_REPO_PATH})",
    )
    parser.add_argument(
        "--components-dir",
        type=Path,
        default=None,
        help="Path to components directory (default: inferred from RPA config's component_filter.path_prefix, or 'images')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: don't create MRs, just show what would be done",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check status of existing MRs, don't onboard new images",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force mode: generate content and create/update MRs even if images are already onboarded or files are up-to-date",
    )
    parser.add_argument(
        "--force-rpa",
        action="store_true",
        help="Force RPA regeneration even when pyxis is already up-to-date. "
            "Useful when RPA templates have been updated and need to be re-applied.",
    )
    parser.add_argument(
        "--wait-for-post-merge-pipeline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Wait for the post-merge pipeline to complete before generating RPAs. "
            "Enabled by default. Use --no-wait-for-post-merge-pipeline to disable.",
    )
    parser.add_argument(
        "--post-merge-pipeline-timeout",
        type=int,
        default=600,
        help="Timeout in seconds for waiting on post-merge pipeline (default: 600 = 10 minutes)",
    )
    parser.add_argument(
        "--wait-for-mr-pipeline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Wait for the MR CI pipeline to complete after creating/updating an MR. "
            "Enabled by default. Use --no-wait-for-mr-pipeline to disable.",
    )
    parser.add_argument(
        "--mr-pipeline-timeout",
        type=int,
        default=3600,
        help="Timeout in seconds for waiting on MR CI pipeline (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("ci/templates/pyxis-repo-config.j2"),
        help="Path to Jinja2 template file for generating YAML content. "
            "Template receives: repositories (list). Default data should be defined in the template. "
            "Default: ci/templates/pyxis-repo-config.j2",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )
    parser.add_argument(
        "--konflux-release-data-repo-path",
        type=str,
        default=None,
        help="GitLab project path for konflux-release-data repository (e.g., 'org/konflux-release-data'). "
            "If not provided, RPA generation will be skipped.",
    )
    parser.add_argument(
        "--konflux-repo-url",
        type=str,
        default=None,
        help="GitLab URL for konflux-release-data repository (defaults to same as --gitlab-url)",
    )
    parser.add_argument(
        "--rpa-config-path",
        type=Path,
        default=Path("ci/konflux_rpa_config.yml"),
        help="Path to RPA configuration file (default: ci/konflux_rpa_config.yml)",
    )
    parser.add_argument(
        "--rpa-template-dir",
        type=Path,
        default=Path("konflux-templates"),
        help="Path to konflux-templates directory (default: konflux-templates)",
    )
    parser.add_argument(
        "--skip-pyxis-mr",
        action="store_true",
        help="Skip pyxis-repo-configs MR creation and only create release-data MR. "
            "Useful when pyxis onboarding is not needed (e.g., images already registered). "
            "Can also be set via 'skip_pyxis_mr: true' on each RPA in the config file.",
    )
    parser.add_argument(
        "--preview-rpa",
        type=Path,
        nargs="?",
        const=Path("rpa-preview"),
        default=None,
        help="Generate RPA files locally for verification and stop. "
            "Writes files to the specified directory (default: ./rpa-preview/). "
            "No remote operations are performed.",
    )

    args = parser.parse_args()

    # Configure logging based on argument
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not args.gitlab_token and args.preview_rpa is None:
        logger.error("GitLab token is required (--gitlab-token or GITLAB_TOKEN env var)")
        return

    # Load RPA config for skip_pyxis_mr check and components_dir inference
    rpa_config = None
    if args.rpa_config_path.exists():
        try:
            rpa_config = load_rpa_config(args.rpa_config_path)
        except Exception as e:
            logger.debug(f"Could not load RPA config: {e}")

    # Determine if we should skip pyxis MR creation
    # CLI argument overrides config; config checks RPA level first, then global
    skip_pyxis_mr = args.skip_pyxis_mr
    if not skip_pyxis_mr and rpa_config:
        rpas = rpa_config.get("rpas", [])
        # Check RPA level first: skip pyxis if ALL RPAs have skip_pyxis_mr: true
        if rpas and all(rpa.get("skip_pyxis_mr", False) for rpa in rpas):
            skip_pyxis_mr = True
            logger.info("skip_pyxis_mr enabled (all RPAs have skip_pyxis_mr: true)")
        # Fall back to global level
        elif rpa_config.get("global", {}).get("skip_pyxis_mr", False):
            skip_pyxis_mr = True
            logger.info("skip_pyxis_mr enabled via RPA config global setting")

    if skip_pyxis_mr:
        logger.info("Skipping pyxis-repo-configs MR creation (--skip-pyxis-mr or config)")

    # Determine components directory
    # Priority: CLI arg > RPA config component_filter.path_prefix > default "images"
    if args.components_dir is not None:
        components_dir = args.components_dir
    elif rpa_config:
        # Try to infer from RPA config's component_filter.path_prefix
        rpas = rpa_config.get("rpas", [])
        path_prefixes = set()
        for rpa in rpas:
            component_filter = rpa.get("component_filter", {})
            path_prefix = component_filter.get("path_prefix", "")
            if path_prefix:
                # Remove trailing slash and use as directory
                path_prefixes.add(path_prefix.rstrip("/"))
        if len(path_prefixes) == 1:
            components_dir = Path(path_prefixes.pop())
            logger.info(f"Inferred components directory from RPA config: {components_dir}")
        else:
            components_dir = Path("images")
            if path_prefixes:
                logger.debug(f"Multiple path_prefixes found ({path_prefixes}), using default: {components_dir}")
    else:
        components_dir = Path("images")

    # Initialize GitLab client (skip in preview-rpa mode)
    gitlab_client = None
    if args.preview_rpa is None:
        gitlab_client = GitLabClient(args.gitlab_url, args.gitlab_token)

    # Validate template file (only required when not skipping pyxis)
    if not skip_pyxis_mr and args.preview_rpa is None:
        assert gitlab_client is not None, "gitlab_client required when not in preview mode"
        if not args.template.exists():
            logger.error(f"Template file not found: {args.template}")
            return
        logger.info(f"Using Jinja2 template: {args.template}")

        # Get pyxis project ID (only needed when not skipping pyxis)
        try:
            project_id = gitlab_client.get_project_id(args.pyxis_repo_configs_project_path)
            logger.info(f"Project ID: {project_id}")
        except Exception as e:
            logger.error(f"Error getting project ID: {e}")
            return

        # Check existing MRs (query GitLab directly, no tracking file needed)
        if not args.dry_run:
            check_existing_mrs(
                gitlab_client,
                project_id,
                pyxis_project_path=args.pyxis_repo_configs_project_path,
                konflux_repo_path=args.konflux_release_data_repo_path,
                konflux_repo_url=args.konflux_repo_url,
                rpa_config_path=args.rpa_config_path,
                rpa_template_dir=args.rpa_template_dir,
                dry_run=args.dry_run,
                force=args.force,
                wait_for_post_merge_pipeline=args.wait_for_post_merge_pipeline,
                post_merge_pipeline_timeout=args.post_merge_pipeline_timeout,
            )

    if args.check_only:
        return

    # Discover components (components_dir already determined above)
    if not components_dir.exists():
        logger.error(f"Components directory not found: {components_dir}")
        return

    components = discover_components(components_dir)
    logger.info(f"Discovered {len(components)} component(s)")

    # Handle preview-rpa mode - generate RPAs locally for verification
    if args.preview_rpa is not None:
        if not components:
            logger.info("No components to process")
            return

        try:
            logger.info(f"Generating RPA preview for {len(components)} component(s)...")
            merged_component_names = [{"name": comp["name"]} for comp in components]
            generate_and_submit_rpas(
                merged_component_names,
                "preview",
                None,  # No gitlab_client needed for preview
                args.konflux_release_data_repo_path or "",
                args.pyxis_repo_configs_project_path,
                args.konflux_repo_url,
                args.rpa_config_path,
                args.rpa_template_dir,
                components_dir=components_dir,
                dry_run=False,
                force=False,
                preview_rpa_dir=args.preview_rpa,
            )
        except Exception as e:
            logger.error(f"Error generating RPA preview: {e}", exc_info=True)
            sys.exit(1)
        return

    # Handle skip_pyxis_mr mode - directly generate RPAs without pyxis MR
    if skip_pyxis_mr:
        if not args.konflux_release_data_repo_path:
            logger.error("--konflux-release-data-repo-path is required when using --skip-pyxis-mr")
            sys.exit(1)

        if not components:
            logger.info("No components to process")
            return

        # Generate RPAs directly without pyxis MR
        try:
            # Use consistent branch name when skipping pyxis (so subsequent runs update the same MR)
            rpa_branch_id = "direct"
            logger.info(f"Generating ReleasePlanAdmissions for {len(components)} component(s)...")

            merged_component_names = [{"name": comp["name"]} for comp in components]
            generate_and_submit_rpas(
                merged_component_names,
                rpa_branch_id,
                gitlab_client,
                args.konflux_release_data_repo_path,
                args.pyxis_repo_configs_project_path,
                args.konflux_repo_url,
                args.rpa_config_path,
                args.rpa_template_dir,
                components_dir=components_dir,
                dry_run=args.dry_run,
                force=args.force or args.force_rpa,
            )
        except Exception as e:
            logger.error(f"Error generating RPAs: {e}", exc_info=True)
            sys.exit(1)
    else:
        # Normal flow: onboard to pyxis first, then generate RPAs
        # All discovered components are candidates for onboarding
        # The update_yaml_file function will handle detecting which already exist
        components_to_onboard = components

        # Onboard all components in a single batch/MR
        # Pass all local components so we can detect and remove entries for deleted ones
        assert gitlab_client is not None, "gitlab_client required for normal flow"
        if components_to_onboard or components:
            try:
                onboard_images_batch(
                    components_to_onboard,
                    gitlab_client,
                    project_id,
                    args.template,
                    args.pyxis_file_path,
                    all_local_images=components,
                    dry_run=args.dry_run,
                    force=args.force,
                    force_rpa=args.force_rpa,
                    pyxis_project_path=args.pyxis_repo_configs_project_path,
                    konflux_repo_path=args.konflux_release_data_repo_path,
                    konflux_repo_url=args.konflux_repo_url,
                    rpa_config_path=args.rpa_config_path,
                    rpa_template_dir=args.rpa_template_dir,
                    wait_for_post_merge_pipeline=args.wait_for_post_merge_pipeline,
                    post_merge_pipeline_timeout=args.post_merge_pipeline_timeout,
                    wait_for_mr_pipeline=args.wait_for_mr_pipeline,
                    mr_pipeline_timeout=args.mr_pipeline_timeout,
                )
            except RuntimeError as e:
                # RuntimeError indicates merge conflicts that couldn't be resolved
                logger.error(f"Error onboarding components: {e}", exc_info=True)
                sys.exit(1)
            except Exception as e:
                logger.error(f"Error onboarding components: {e}", exc_info=True)
                sys.exit(1)
        else:
            logger.info("No components to process")

    # Check and manage konflux MRs at the end of execution
    if not args.dry_run and args.konflux_release_data_repo_path:
        assert gitlab_client is not None, "gitlab_client required for konflux MR checks"
        try:
            konflux_project_id = gitlab_client.get_project_id(args.konflux_release_data_repo_path)
            check_konflux_mrs(
                gitlab_client,
                konflux_project_id,
                args.konflux_release_data_repo_path,
                dry_run=args.dry_run,
            )
        except RuntimeError as e:
            # RuntimeError indicates a failed pipeline that needs to be fixed
            logger.error(f"Error checking konflux MRs: {e}", exc_info=True)
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error checking konflux MRs: {e}", exc_info=True)
            sys.exit(1)


def check_konflux_mrs(
    gitlab_client: GitLabClient,
    konflux_project_id: int,
    konflux_repo_path: str,
    dry_run: bool = False,
) -> None:
    """Check status of konflux-release-data MRs and merge if ready.

    This function is stateless - it queries GitLab for open MRs matching the
    branch pattern used for RPA updates.
    """
    # Query GitLab for open MRs with the RPA branch pattern
    try:
        all_open_mrs = gitlab_client.list_merge_requests(
            konflux_project_id,
            state="opened",
        )
        # Filter to only MRs with our branch pattern
        konflux_mrs = [
            mr for mr in all_open_mrs
            if mr.get("source_branch", "").startswith(KONFLUX_BRANCH_PREFIX)
        ]
    except Exception as e:
        logger.warning(f"Could not list open MRs in konflux repo: {e}")
        return

    if not konflux_mrs:
        logger.info(f"No open MRs found matching branch pattern {KONFLUX_BRANCH_PREFIX}*")
        return

    logger.info(f"Checking status of {len(konflux_mrs)} konflux-release-data merge request(s)...")

    for mr in konflux_mrs:
        konflux_mr_id = mr["iid"]
        project_path = konflux_repo_path

        try:
            # Refresh MR details
            mr = gitlab_client.get_merge_request(konflux_project_id, konflux_mr_id)
            state = mr.get("state")
            merge_status = mr.get("merge_status", "unknown")
            detailed_merge_status = mr.get("detailed_merge_status", "unknown")

            # Skip if not open
            if state != "opened":
                continue

            # Check for merge conflicts
            if merge_status == "cannot_be_merged":
                logger.error(
                    f"Konflux MR {konflux_mr_id} ({project_path}) has merge conflicts. "
                    f"Please resolve conflicts manually in GitLab."
                )
                continue

            # Check pipeline status
            try:
                pipelines = gitlab_client.get_merge_request_pipelines(konflux_project_id, konflux_mr_id)
                pipeline_success = False
                if pipelines:
                    latest_pipeline = pipelines[0]
                    pipeline_status = latest_pipeline.get("status", "unknown")
                    pipeline_web_url = latest_pipeline.get("web_url", "")

                    status_emoji = {
                        "success": "✓",
                        "failed": "✗",
                        "running": "⟳",
                        "pending": "⏳",
                        "canceled": "⊘",
                        "skipped": "⊘",
                    }.get(pipeline_status, "?")

                    logger.info(
                        f"Konflux MR {konflux_mr_id} ({project_path}) CI pipeline status: "
                        f"{status_emoji} {pipeline_status}"
                        + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                    )

                    # If pipeline is still running/pending, wait up to 1 hour for it to finish
                    if pipeline_status in ("running", "pending", "created"):
                        import time
                        max_wait_seconds = 3600  # 1 hour
                        poll_interval = 30
                        waited = 0
                        logger.info(
                            f"Waiting for CI pipeline to finish on konflux MR {konflux_mr_id} "
                            f"(up to {max_wait_seconds // 60} min)"
                            + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                        )
                        while pipeline_status in ("running", "pending", "created") and waited < max_wait_seconds:
                            time.sleep(poll_interval)
                            waited += poll_interval
                            try:
                                pipelines = gitlab_client.get_merge_request_pipelines(konflux_project_id, konflux_mr_id)
                                if pipelines:
                                    latest_pipeline = pipelines[0]
                                    pipeline_status = latest_pipeline.get("status", "unknown")
                                    pipeline_web_url = latest_pipeline.get("web_url", pipeline_web_url)
                            except Exception:
                                pass
                            if waited % 300 == 0:
                                logger.info(
                                    f"Still waiting for CI pipeline on konflux MR {konflux_mr_id}... "
                                    f"({waited // 60} min elapsed, status: {pipeline_status})"
                                )

                        # Log final pipeline status after waiting
                        final_emoji = {
                            "success": "✓", "failed": "✗", "running": "⟳",
                            "pending": "⏳", "canceled": "⊘", "skipped": "⊘",
                        }.get(pipeline_status, "?")
                        if waited > 0:
                            logger.info(
                                f"Konflux MR {konflux_mr_id} ({project_path}) CI pipeline result after {waited // 60} min: "
                                f"{final_emoji} {pipeline_status}"
                                + (f" ({pipeline_web_url})" if pipeline_web_url else "")
                            )

                    pipeline_success = pipeline_status == "success"

                    if pipeline_status == "failed":
                        logger.error(
                            f"Konflux MR {konflux_mr_id} ({project_path}) CI pipeline has failed. "
                            f"Please fix the issues before continuing."
                            + (f" See: {pipeline_web_url}" if pipeline_web_url else "")
                        )
                        logger.info(
                            "Hint: If you've fixed the RPA templates locally, use --force-rpa to "
                            "regenerate and push updated RPAs to the existing MR."
                        )
                        raise RuntimeError(
                            f"Konflux MR {konflux_mr_id} ({project_path}) CI pipeline failed. "
                            f"Fix the issues in the pipeline before continuing."
                        )
                else:
                    logger.info(f"Konflux MR {konflux_mr_id} ({project_path}) has no CI pipelines")
            except RuntimeError:
                raise
            except Exception as e:
                logger.debug(f"Could not get pipeline status for konflux MR {konflux_mr_id}: {e}")
                pipeline_success = False

            # Check approval status
            try:
                approvals = gitlab_client.get_merge_request_approvals(konflux_project_id, konflux_mr_id)
                approvals_met = False
                if approvals:
                    required = approvals.get("approvals_required", 0)
                    approved = len(approvals.get("approved_by", []))
                    approvals_left = max(0, required - approved)

                    if required == 0:
                        logger.info(f"Konflux MR {konflux_mr_id} ({project_path}) approval status: ✓ No approvals required")
                        approvals_met = True
                    elif approved >= required:
                        logger.info(f"Konflux MR {konflux_mr_id} ({project_path}) approval status: ✓ Approved ({approved}/{required} approvals)")
                        approvals_met = True
                    else:
                        logger.info(
                            f"Konflux MR {konflux_mr_id} ({project_path}) approval status: "
                            f"⏳ Pending ({approved}/{required} approvals, {approvals_left} remaining)"
                        )

                        # Attempt to approve via API if CI passed
                        if pipeline_success:
                            logger.info(f"Attempting to approve konflux MR {konflux_mr_id} via API...")
                            try:
                                approve_result = gitlab_client.approve_merge_request(konflux_project_id, konflux_mr_id)
                                if approve_result:
                                    logger.info(f"✓ Successfully approved konflux MR {konflux_mr_id}")
                                    approvals_met = True
                                else:
                                    logger.info(
                                        f"Could not approve konflux MR {konflux_mr_id} via API "
                                        "(may require manual approval in GitLab UI)"
                                    )
                            except Exception as e:
                                logger.debug(f"Approval attempt failed for konflux MR {konflux_mr_id}: {e}")
                                logger.info(
                                    f"Could not approve konflux MR {konflux_mr_id} via API "
                                    "(may require manual approval in GitLab UI)"
                                )
                else:
                    logger.debug(f"Could not get approval status for konflux MR {konflux_mr_id}")
                    approvals_met = True  # Assume no approvals required if we can't check
            except Exception as e:
                logger.debug(f"Could not get approval status for konflux MR {konflux_mr_id}: {e}")
                approvals_met = True  # Assume no approvals required if we can't check

            # Refresh MR details after pipeline/approval checks (status may have changed)
            if pipeline_success:
                mr = gitlab_client.get_merge_request(konflux_project_id, konflux_mr_id)
                merge_status = mr.get("merge_status", merge_status)
                detailed_merge_status = mr.get("detailed_merge_status", detailed_merge_status)

            # Check if ready to merge
            can_merge = mr.get("user", {}).get("can_merge", False)

            if pipeline_success and approvals_met and (merge_status == "can_be_merged" or can_merge):
                logger.info(
                    f"Konflux MR {konflux_mr_id} ({project_path}) is ready to merge "
                    f"(pipeline: success, approvals: met, merge_status: {merge_status}, detailed_status: {detailed_merge_status})"
                )

                if detailed_merge_status in ("checking", "ci_still_running"):
                    import time
                    logger.debug("Waiting 2 seconds for GitLab to update merge status...")
                    time.sleep(2)
                    mr = gitlab_client.get_merge_request(konflux_project_id, konflux_mr_id)
                    detailed_merge_status = mr.get("detailed_merge_status", detailed_merge_status)

                if detailed_merge_status == "mergeable":
                    # Proactively rebase if needed before merge attempt
                    # This avoids failed merge attempts and subsequent reactive rebases
                    should_be_rebased = mr.get("should_be_rebased", False)
                    if should_be_rebased:
                        logger.info(f"Rebasing konflux MR {konflux_mr_id} to ensure it's up-to-date with target branch...")
                        try:
                            import time
                            rebase_result = gitlab_client.rebase_merge_request(konflux_project_id, konflux_mr_id)
                            logger.debug(f"Rebase result: {rebase_result}")

                            # Wait for rebase to complete
                            for _ in range(30):  # Wait up to 60 seconds
                                time.sleep(2)
                                mr_check = gitlab_client.get_merge_request(konflux_project_id, konflux_mr_id)
                                if not mr_check.get("rebase_in_progress", False):
                                    break
                                logger.debug("Rebase in progress, waiting...")

                            # Wait for MR to become mergeable after rebase (CI must pass)
                            max_wait_seconds = 3600  # 1 hour
                            poll_interval = 30
                            waited = 0
                            pipeline_url_logged = False

                            while waited < max_wait_seconds:
                                mr = gitlab_client.get_merge_request(konflux_project_id, konflux_mr_id)
                                detailed_merge_status = mr.get("detailed_merge_status", "unknown")
                                logger.debug(f"MR status after rebase: detailed_merge_status={detailed_merge_status} (waited {waited}s)")

                                if detailed_merge_status == "mergeable":
                                    logger.info(f"Konflux MR {konflux_mr_id} is mergeable after rebase")
                                    break

                                if detailed_merge_status in ("approvals_syncing", "checking", "ci_still_running", "ci_must_pass"):
                                    if not pipeline_url_logged:
                                        try:
                                            pipelines = gitlab_client.get_merge_request_pipelines(konflux_project_id, konflux_mr_id)
                                            if pipelines:
                                                latest_pl = pipelines[0]
                                                pl_web_url = latest_pl.get("web_url", "")
                                                pl_status = latest_pl.get("status", "unknown")
                                                logger.info(
                                                    f"Waiting for post-rebase CI pipeline on MR {konflux_mr_id} "
                                                    f"(status: {pl_status}, up to {max_wait_seconds // 60} min)"
                                                    + (f" ({pl_web_url})" if pl_web_url else "")
                                                )
                                                pipeline_url_logged = True
                                        except Exception:
                                            pass

                                    time.sleep(poll_interval)
                                    waited += poll_interval
                                    if waited % 300 == 0:
                                        logger.info(f"Still waiting for post-rebase CI on MR {konflux_mr_id}... ({waited // 60} min elapsed)")
                                elif detailed_merge_status in ("not_approved", "blocked_status", "not_open"):
                                    logger.warning(f"MR {konflux_mr_id} cannot be merged after rebase: {detailed_merge_status}")
                                    break
                                else:
                                    time.sleep(poll_interval)
                                    waited += poll_interval

                            if detailed_merge_status != "mergeable":
                                logger.warning(
                                    f"Konflux MR {konflux_mr_id} not mergeable after rebase wait: {detailed_merge_status}. "
                                    f"Manual intervention may be required."
                                )
                                continue  # Skip to next MR
                        except Exception as e:
                            logger.warning(f"Failed to proactively rebase MR {konflux_mr_id}: {e}")
                            # Continue with merge attempt anyway - it might still work

                    try:
                        squash_on_merge = mr.get("squash_on_merge", False)
                        merge_result = gitlab_client.merge_merge_request(
                            konflux_project_id, konflux_mr_id, squash=squash_on_merge
                        )
                        if merge_result.get("state") == "merged":
                            logger.info(f"✓ Successfully merged konflux MR {konflux_mr_id} ({project_path})")

                            # Wait for post-merge pipeline on target branch
                            target_branch = mr.get("target_branch", "main")
                            import time
                            time.sleep(3)  # Wait a moment for pipeline to be triggered
                            logger.info(f"Waiting for post-merge pipeline on {target_branch} to complete...")
                            try:
                                pipeline_ok, pl_status, pl_url = wait_for_pipeline(
                                    gitlab_client, konflux_project_id, target_branch,
                                    timeout_seconds=3600, poll_interval=30,
                                )
                                if not pipeline_ok:
                                    logger.warning(
                                        f"Konflux post-merge pipeline on {target_branch} did not succeed: {pl_status}"
                                        + (f" ({pl_url})" if pl_url else "")
                                    )
                            except Exception as e:
                                logger.debug(f"Could not check post-merge pipeline status: {e}")
                        else:
                            logger.warning(f"Konflux MR {konflux_mr_id} merge request returned state: {merge_result.get('state')}")
                    except Exception as e:
                        error_msg = str(e)
                        if hasattr(e, "response") and e.response is not None:
                            status_code = e.response.status_code
                            try:
                                error_body = e.response.json()
                                error_detail = error_body.get("message", str(error_body))
                            except Exception:
                                error_detail = e.response.text

                            if status_code == 401:
                                logger.warning(
                                    f"Could not merge konflux MR {konflux_mr_id}: GitLab token lacks permission to merge MRs (HTTP 401). "
                                    f"Please ensure your token has 'api' scope with 'write_repository' permission."
                                )
                            elif status_code == 422:
                                # Log detailed MR state for debugging
                                logger.debug(
                                    f"Konflux MR {konflux_mr_id} merge failed (422). MR details: "
                                    f"merge_status={mr.get('merge_status')}, "
                                    f"detailed_merge_status={mr.get('detailed_merge_status')}, "
                                    f"has_conflicts={mr.get('has_conflicts')}, "
                                    f"merge_error={mr.get('merge_error')}, "
                                    f"rebase_in_progress={mr.get('rebase_in_progress')}, "
                                    f"should_be_rebased={mr.get('should_be_rebased')}, "
                                    f"ff_only_enabled={mr.get('ff_only_enabled')}, "
                                    f"error_detail={error_detail}"
                                )

                                # Try rebasing first if merge failed, with retry logic for race conditions
                                max_rebase_attempts = 3

                                for rebase_attempt in range(1, max_rebase_attempts + 1):
                                    if rebase_attempt == 1:
                                        logger.info(f"Attempting to rebase konflux MR {konflux_mr_id} before merging...")
                                    else:
                                        logger.info(
                                            f"Retrying rebase for konflux MR {konflux_mr_id} "
                                            f"(attempt {rebase_attempt}/{max_rebase_attempts})..."
                                        )

                                    try:
                                        rebase_result = gitlab_client.rebase_merge_request(konflux_project_id, konflux_mr_id)
                                        logger.debug(f"Rebase result: {rebase_result}")

                                        # Wait for rebase to complete
                                        import time
                                        for _ in range(30):  # Wait up to 60 seconds
                                            time.sleep(2)
                                            mr_check = gitlab_client.get_merge_request(konflux_project_id, konflux_mr_id)
                                            if not mr_check.get("rebase_in_progress", False):
                                                break
                                            logger.debug("Rebase in progress, waiting...")

                                        # Wait for MR to become mergeable after rebase (up to 1 hour)
                                        # After rebase, GitLab re-runs CI so we may need to wait for the pipeline.
                                        max_wait_seconds = 3600  # 1 hour
                                        poll_interval = 30  # seconds between polls
                                        waited = 0
                                        new_merge_status = "unknown"
                                        pipeline_url_logged = False

                                        while waited < max_wait_seconds:
                                            mr_after_rebase = gitlab_client.get_merge_request(konflux_project_id, konflux_mr_id)
                                            new_merge_status = mr_after_rebase.get("detailed_merge_status", "unknown")
                                            logger.debug(f"MR status after rebase: detailed_merge_status={new_merge_status} (waited {waited}s)")

                                            if new_merge_status == "mergeable":
                                                break

                                            if new_merge_status in ("approvals_syncing", "checking", "ci_still_running", "ci_must_pass"):
                                                # Log pipeline info once so the user can follow along
                                                if not pipeline_url_logged:
                                                    try:
                                                        pipelines = gitlab_client.get_merge_request_pipelines(konflux_project_id, konflux_mr_id)
                                                        if pipelines:
                                                            latest_pl = pipelines[0]
                                                            pl_web_url = latest_pl.get("web_url", "")
                                                            pl_status = latest_pl.get("status", "unknown")
                                                            logger.info(
                                                                f"Waiting for post-rebase CI pipeline to finish on MR {konflux_mr_id} "
                                                                f"(status: {pl_status}, up to {max_wait_seconds // 60} min)"
                                                                + (f" ({pl_web_url})" if pl_web_url else "")
                                                            )
                                                            pipeline_url_logged = True
                                                    except Exception:
                                                        pass
                                                    if not pipeline_url_logged:
                                                        logger.info(
                                                            f"Waiting for MR {konflux_mr_id} to become mergeable after rebase "
                                                            f"(status: {new_merge_status}, up to {max_wait_seconds // 60} min)..."
                                                        )
                                                        pipeline_url_logged = True

                                                time.sleep(poll_interval)
                                                waited += poll_interval

                                                # Log progress every 5 minutes
                                                if waited % 300 == 0:
                                                    logger.info(
                                                        f"Still waiting for MR {konflux_mr_id} post-rebase CI... "
                                                        f"({waited // 60} min elapsed, status: {new_merge_status})"
                                                    )
                                            else:
                                                # Non-transient status (e.g. not_open, conflict, etc.) — stop waiting
                                                break

                                        if new_merge_status == "mergeable":
                                            # Brief pause to let GitLab state stabilize before merge
                                            time.sleep(5)

                                            # Re-check approval status after rebase (GitLab may invalidate approvals)
                                            try:
                                                approvals = gitlab_client.get_merge_request_approvals(konflux_project_id, konflux_mr_id)
                                                approvals_required = approvals.get("approvals_required", 0)
                                                approvals_left = approvals.get("approvals_left", 0)
                                                if approvals_required > 0 and approvals_left > 0:
                                                    logger.info(f"Re-approving MR {konflux_mr_id} after rebase...")
                                                    try:
                                                        gitlab_client.approve_merge_request(konflux_project_id, konflux_mr_id)
                                                        logger.info(f"✓ Re-approved MR {konflux_mr_id}")
                                                        time.sleep(2)  # Brief pause for approval to register
                                                    except Exception as approve_err:
                                                        logger.debug(f"Re-approval attempt failed: {approve_err}")
                                            except Exception as check_err:
                                                logger.debug(f"Could not check approval status: {check_err}")

                                            try:
                                                merge_result = gitlab_client.merge_merge_request(
                                                    konflux_project_id, konflux_mr_id, squash=squash_on_merge
                                                )
                                                if merge_result.get("state") == "merged":
                                                    logger.info(f"✓ Successfully merged konflux MR {konflux_mr_id} ({project_path}) after rebase")

                                                    # Wait for post-merge pipeline on target branch
                                                    target_branch = mr.get("target_branch", "main")
                                                    time.sleep(3)  # Wait a moment for pipeline to be triggered
                                                    logger.info(f"Waiting for post-merge pipeline on {target_branch} to complete...")
                                                    try:
                                                        pipeline_ok, pl_status, pl_url = wait_for_pipeline(
                                                            gitlab_client, konflux_project_id, target_branch,
                                                            timeout_seconds=3600, poll_interval=30,
                                                        )
                                                        if not pipeline_ok:
                                                            logger.warning(
                                                                f"Konflux post-merge pipeline on {target_branch} did not succeed: {pl_status}"
                                                                + (f" ({pl_url})" if pl_url else "")
                                                            )
                                                    except Exception as pl_err:
                                                        logger.debug(f"Could not check post-merge pipeline status: {pl_err}")
                                                    break  # Exit retry loop on success
                                                else:
                                                    logger.warning(
                                                        f"Could not merge konflux MR {konflux_mr_id} after rebase: {merge_result.get('state')}. "
                                                        f"Please merge manually in the GitLab UI."
                                                    )
                                                    break  # Non-retryable failure
                                            except Exception as merge_err:
                                                merge_err_msg = str(merge_err)
                                                # Check if this is a retryable error (race conditions, transient 422, etc.)
                                                is_retryable = False
                                                if hasattr(merge_err, "response") and merge_err.response is not None:
                                                    status_code = merge_err.response.status_code
                                                    # 405 = method not allowed (often race condition)
                                                    # 422 = unprocessable entity (often approvals not synced yet after rebase)
                                                    is_retryable = status_code in (405, 422)
                                                if not is_retryable:
                                                    is_retryable = "cannot be merged" in merge_err_msg.lower()

                                                if rebase_attempt < max_rebase_attempts and is_retryable:
                                                    logger.info(
                                                        f"Merge failed after rebase (likely transient, will retry). "
                                                        f"Error: {merge_err_msg} ({rebase_attempt}/{max_rebase_attempts})"
                                                    )
                                                    time.sleep(10)  # Brief pause before retry
                                                    continue  # Retry the rebase+merge cycle
                                                else:
                                                    logger.warning(
                                                        f"Could not merge konflux MR {konflux_mr_id} after rebase: {merge_err_msg}. "
                                                        f"Please merge manually in the GitLab UI."
                                                    )
                                                    break  # Give up after max retries or non-retryable error
                                        else:
                                            if rebase_attempt < max_rebase_attempts and new_merge_status not in ("not_approved", "blocked_status", "not_open", "conflict"):
                                                logger.info(
                                                    f"MR not mergeable after rebase wait (status: {new_merge_status}). "
                                                    f"Retrying... ({rebase_attempt}/{max_rebase_attempts})"
                                                )
                                                continue
                                            else:
                                                logger.warning(
                                                    f"Could not merge konflux MR {konflux_mr_id}: Branch not mergeable after rebase. "
                                                    f"Status: {new_merge_status} (waited {waited}s). Please merge manually in the GitLab UI."
                                                )
                                                break  # Give up
                                    except Exception as rebase_error:
                                        if rebase_attempt < max_rebase_attempts:
                                            logger.info(
                                                f"Rebase attempt {rebase_attempt} failed: {rebase_error}. "
                                                f"Retrying... ({rebase_attempt}/{max_rebase_attempts})"
                                            )
                                            time.sleep(5)  # Brief pause before retry
                                            continue
                                        else:
                                            logger.debug(f"Rebase attempt failed: {rebase_error}")
                                            logger.warning(
                                                f"Could not merge konflux MR {konflux_mr_id}: Branch cannot be merged. "
                                                f"Rebase failed after {max_rebase_attempts} attempts. Please merge manually in the GitLab UI. "
                                                f"Error: {error_detail}"
                                            )
                            else:
                                logger.warning(f"Could not merge konflux MR {konflux_mr_id} (HTTP {status_code}): {error_msg}")
                        else:
                            logger.warning(f"Could not merge konflux MR {konflux_mr_id}: {error_msg}")
            else:
                logger.debug(
                    f"Konflux MR {konflux_mr_id} ({project_path}) cannot be merged yet "
                    f"(pipeline: {pipeline_success}, approvals: {approvals_met}, merge_status: {merge_status}, "
                    f"detailed_status: {detailed_merge_status}, can_merge: {can_merge})"
                )

        except RuntimeError:
            raise
        except Exception as e:
            logger.warning(f"Could not check konflux MR {konflux_mr_id}: {e}")


if __name__ == "__main__":
    main()
