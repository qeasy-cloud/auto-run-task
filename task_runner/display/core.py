"""
Core display components: console singleton, constants, and utility helpers.
"""

import sys

from rich.console import Console

# ─── Singleton Console ───────────────────────────────────────────

console = Console(highlight=False)

# ─── Constants ───────────────────────────────────────────────────

STATUS_ICONS = {
    "not-started": "⬜",
    "in-progress": "🔄",
    "completed": "✅",
    "failed": "❌",
    "interrupted": "⚡",
    "skipped": "⏭️",
    "planned": "📋",
    "active": "🟢",
    "archived": "📦",
    "running": "🔄",
    "partial": "⚠️",
}

STATUS_STYLES = {
    "not-started": "dim",
    "in-progress": "yellow",
    "completed": "green",
    "failed": "red",
    "interrupted": "yellow",
    "planned": "dim",
    "active": "green",
    "archived": "dim",
}

SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

LOGO = r"""
   _____          __          ______           __      ____
  /  _  \  __ ___/  |_  ____ \__   _|____   _/  |_  _/_   |
 /  /_\  \|  |  \   __\/  _ \  |   |__  \  \   __\ \   ___|
/    |    \  |  /|  | (  <_> ) |   |/ __ \_/\  |    |  |
\____|__  /____/ |__|  \____/  |___(____  /  \__|    |__|
        \/                              \/  v3.0
"""


# ─── Terminal Title ──────────────────────────────────────────────


def set_terminal_title(text: str):
    """Set terminal window title via OSC escape sequence."""
    try:
        sys.stderr.write(f"\033]0;{text}\007")
        sys.stderr.flush()
    except OSError:
        pass


def reset_terminal_title():
    """Reset terminal title to default."""
    try:
        sys.stderr.write("\033]0;\007")
        sys.stderr.flush()
    except OSError:
        pass


# ─── Internal Helpers ────────────────────────────────────────────


def format_elapsed(elapsed: float) -> str:
    """Format elapsed seconds into a human-readable string."""
    total_secs = int(elapsed)
    hours, remainder = divmod(total_secs, 3600)
    mins, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {mins:02d}m {secs:02d}s"
    elif mins > 0:
        return f"{mins}m {secs:02d}s"
    else:
        return f"{secs}s"


# Keep _format_elapsed as alias for backward compat within display submodules
_format_elapsed = format_elapsed
