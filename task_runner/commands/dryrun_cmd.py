"""
Dry-run command: generate prompts without executing.
"""

from .run_cmd import _execute


def handle_dryrun(args) -> int:
    """Dry-run: generate prompts only, no execution."""
    return _execute(args, dry_run=True)
