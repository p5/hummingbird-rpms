#!/usr/bin/python3
"""Script to delete Konflux comments on GitLab MRs."""

import argparse
from enum import Enum
import re
import typing

from cki_lib import gitlab
from gitlab.v4 import objects

# Constants
MAX_COMMENT_DISPLAY_LENGTH = 100


def clean_comment_text(text: str) -> str:
    """Remove HTML and basic markdown formatting from comment text."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove basic markdown formatting
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Bold: **text** -> text
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # Italic: *text* -> text
    text = re.sub(r"`(.*?)`", r"\1", text)  # Code: `text` -> text
    text = re.sub(r"#+\s*", "", text)  # Headers: # text -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links: [text](url) -> text

    # Clean up extra whitespace
    return re.sub(r"\s+", " ", text).strip()


class CommentType(Enum):
    """Enum class defining comment types and their regex patterns, organized by category."""

    # failed
    BUILD_FAILED = ("failed", r"Konflux .*-pull-request has failed")
    TEST_FAILED = ("failed", r"Integration test for snapshot .* and scenario .* has failed")

    # success
    BUILD_SUCCESS = ("success", r"Konflux .*-pull-request has successfully validated your commit")
    TEST_SUCCESS = ("success", r"Integration test for snapshot .* and scenario .* has passed")

    # pending
    BUILD_QUEUED = ("pending", r"PipelineRun.*has been queued")
    BUILD_RUNNING = ("pending", r"Starting Pipelinerun .*-pull-request-.* in namespace")
    BUILD_CANCELLED = ("pending", r'task .* has the status "TaskRunCancelled"')

    TEST_PENDING = (
        "pending",
        r"Integration test for scenario .* is pending because build "
        r"pipelinerun is still running",
    )

    TEST_SKIPPED = (
        "pending",
        r"Integration test for scenario .* has not run and is considered as "
        r"failed because the build pipelinerun failed",
    )

    def __init__(self, category: str, pattern: str) -> None:
        """Initialize CommentType with category and regex pattern."""
        self.category = category
        self.pattern = pattern

    def get_pattern(self) -> str:
        """Return the regex pattern for this comment type."""
        return self.pattern


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the script."""
    comment_type_choices = [ct.name.lower().replace("_", "-") for ct in CommentType]
    available_categories = list({ct.category for ct in CommentType})

    parser = argparse.ArgumentParser(description="Delete Konflux comments on GitLab MRs")
    parser.add_argument("url", help="GitLab URL (MR or project)")
    parser.add_argument(
        "--comment-type",
        nargs="+",
        choices=comment_type_choices,
        help="Specific comment types to delete",
    )
    parser.add_argument(
        "--comment-category",
        nargs="+",
        choices=available_categories,
        help="Select comments by category",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include all comment types (overrides other options)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting comments",
    )
    return parser.parse_args()


def should_delete_comment(note_body: str, comment_types: list[str]) -> bool:
    """Determine if a comment should be deleted based on its content and selected types."""
    cleaned_body = clean_comment_text(note_body)

    for comment_type in comment_types:
        enum_name = comment_type.upper().replace("-", "_")
        try:
            comment_type_enum = CommentType[enum_name]
            pattern = comment_type_enum.get_pattern()
            if re.search(pattern, cleaned_body, re.IGNORECASE):
                return True
        except KeyError:
            continue

    return False


def get_comment_types(args: argparse.Namespace) -> list[str]:
    """Determine which comment types to process based on arguments."""
    if args.all:
        return [ct.name.lower().replace("_", "-") for ct in CommentType]

    comment_types = []

    if args.comment_type:
        comment_types.extend(args.comment_type)
    elif args.comment_category:
        category_types = [
            ct.name.lower().replace("_", "-")
            for ct in CommentType
            if ct.category in args.comment_category
        ]
        comment_types.extend(category_types)
    else:
        category_types = [
            ct.name.lower().replace("_", "-") for ct in CommentType if ct.category in ["pending"]
        ]
        comment_types.extend(category_types)

    return list(dict.fromkeys(comment_types))


def get_merge_requests(url: str) -> typing.Iterable[objects.MergeRequest]:
    """Get list of merge requests from the given URL."""
    gl_mr_or_project = gitlab.parse_gitlab_url(url)[1]
    if type(gl_mr_or_project) is objects.Project:
        return typing.cast(
            "typing.Iterable[objects.MergeRequest]",
            gl_mr_or_project.mergerequests.list(state="opened", iterator=True),
        )
    # gl_mr_or_project is a MergeRequest when it's not a Project
    return [typing.cast("objects.MergeRequest", gl_mr_or_project)]


def process_merge_request(
    gl_mr: objects.MergeRequest,
    comment_types: list[str],
    *,
    dry_run: bool,
) -> None:
    """Process a single merge request and return whether any failures occurred."""
    deleted_count = 0
    would_delete_count = 0

    print(f"MR !{gl_mr.iid}: Comment types: {', '.join(comment_types)}")

    pac_notes = [
        note
        for note in gl_mr.notes.list(all=True, per_page=200)
        if note.author["name"] == "pipelines-as-code"
    ]

    for note in pac_notes:
        if should_delete_comment(note.body, comment_types):
            first_line = note.body.split("\n")[0]
            truncated_line = first_line[:MAX_COMMENT_DISPLAY_LENGTH] + (
                "..." if len(first_line) > MAX_COMMENT_DISPLAY_LENGTH else ""
            )
            if dry_run:
                print(f"MR !{gl_mr.iid}: Would delete comment: {truncated_line}")
                would_delete_count += 1
            else:
                print(f"MR !{gl_mr.iid}: Deleting comment: {truncated_line}")
                note.delete()
                deleted_count += 1

    if dry_run and would_delete_count > 0:
        print(f"MR !{gl_mr.iid}: Would delete {would_delete_count} comments (dry-run mode)")
    elif deleted_count > 0:
        print(f"MR !{gl_mr.iid}: Total deleted {deleted_count} comments")


def main() -> None:
    """Main function to delete Konflux comments on GitLab MRs."""
    args = parse_arguments()
    comment_types = get_comment_types(args)
    gl_mrs = get_merge_requests(args.url)
    for gl_mr in gl_mrs:
        process_merge_request(gl_mr, comment_types, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
