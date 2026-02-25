"""
Utility message display functions (errors, warnings, info, etc.).
"""

from rich import box
from rich.panel import Panel
from rich.table import Table

from .core import console


def show_error(msg: str):
    """Display an error message."""
    console.print(f"[bold red]❌ {msg}[/bold red]")


def show_warning(msg: str):
    """Display a warning message."""
    console.print(f"[yellow]⚠️  {msg}[/yellow]")


def show_info(msg: str):
    """Display an info message."""
    console.print(f"[dim]ℹ️  {msg}[/dim]")


def show_interrupt():
    """Display CTRL+C interrupt message."""
    console.print("\n[bold yellow]⚠️  CTRL+C received — terminating current task...[/bold yellow]")


def show_force_exit():
    """Display force exit message."""
    console.print("\n[bold red]❌ Force exit! (double CTRL+C)[/bold red]")


def show_delay(seconds: int, task_no_next: str = ""):
    """Display a countdown for the anti-detection delay between tasks.

    Note: The main countdown loop lives in ``TaskExecutor._inter_task_delay``
    so it can check ``self.interrupted`` each tick.  This function is kept as a
    simple helper for any standalone usage.
    """
    import sys
    import time as _time

    if seconds <= 0:
        return

    label = f"next: {task_no_next}" if task_no_next else "next task"
    try:
        for remaining in range(seconds, 0, -1):
            sys.stdout.write(
                f"\r  ⏳ Waiting {remaining}s before {label} (anti-rate-limit)..."
            )
            sys.stdout.flush()
            _time.sleep(1)
        sys.stdout.write(f"\r  ⏳ Delay complete, resuming execution.{' ' * 40}\n")
        sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.write(f"\r  ⏳ Delay interrupted.{' ' * 50}\n")
        sys.stdout.flush()
        raise


def show_tool_not_found(tool_name: str):
    """Display tool-not-found error with help."""
    console.print(
        Panel(
            f"[red]CLI tool '[bold]{tool_name}[/bold]' not found in PATH![/red]\n\n"
            f"Make sure '{tool_name}' is installed and accessible.\n"
            f"You can verify with: [cyan]which {tool_name}[/cyan]",
            title="[red]Tool Not Found[/red]",
            border_style="red",
            padding=(1, 2),
        )
    )


def show_available_models(tool_name: str, models: list[str], default: str | None):
    """Display available models for a tool."""
    table = Table(
        title=f"Available Models for '{tool_name}'",
        box=box.SIMPLE,
        header_style="bold",
    )
    table.add_column("Model", style="cyan")
    table.add_column("Default", width=8, justify="center")

    for m in models:
        is_default = "★" if m == default else ""
        table.add_row(m, is_default)

    console.print(table)
