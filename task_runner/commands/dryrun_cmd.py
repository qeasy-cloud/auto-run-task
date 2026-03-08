"""
Dry-run command: generate prompts without executing.
"""

from .run_cmd import _dispatch


def handle_dryrun(args) -> int:
    """Dry-run: generate prompts only, no execution."""
    return _dispatch(args, dry_run=True)
