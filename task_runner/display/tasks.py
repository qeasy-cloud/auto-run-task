"""
Task execution display: task lists, start/result panels, skip/dry-run markers.
"""

from datetime import datetime

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .core import STATUS_ICONS, STATUS_STYLES, _format_elapsed, console

# ─── Task List (Legacy) ─────────────────────────────────────────


def show_task_list(tasks: list[dict]):
    """Display a rich table of all tasks with their statuses (legacy)."""
    table = Table(
        title="📋 Task Plan",
        box=box.ROUNDED,
        show_lines=False,
        title_style="bold",
        header_style="bold bright_blue",
        row_styles=["", "dim"],
    )

    table.add_column("No", style="bold", width=8, no_wrap=True)
    table.add_column("Status", width=6, justify="center")
    table.add_column("Type", width=8)
    table.add_column("Module", min_width=24, max_width=36)
    table.add_column("Task Name", min_width=30)
    table.add_column("Est", width=6, justify="right")

    for t in tasks:
        status = t.get("status", "not-started")
        icon = STATUS_ICONS.get(status, "❓")
        style = STATUS_STYLES.get(status, "")

        table.add_row(
            t.get("task_no", "?"),
            icon,
            t.get("type", ""),
            t.get("module", ""),
            t.get("task_name", ""),
            f"{t.get('estimated_minutes', '?')}m",
            style=style if status in ("failed",) else "",
        )

    console.print(table)

    total = len(tasks)
    done = sum(1 for t in tasks if t.get("status") == "completed")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    console.print(
        f"\n  [bold]Total:[/bold] {total}  │  "
        f"[green]Done: {done}[/green]  │  "
        f"[red]Failed: {failed}[/red]  │  "
        f"[yellow]Remaining: {total - done}[/yellow]"
    )
    console.print()


# ─── Task List (V3) ─────────────────────────────────────────────


def show_task_list_v3(task_set_name: str, tasks: list):
    """Display a v3 task list with priority and description columns."""
    table = Table(
        title=f"📋 Task Set: {task_set_name}",
        box=box.ROUNDED,
        show_lines=False,
        title_style="bold",
        header_style="bold bright_blue",
        row_styles=["", "dim"],
    )

    table.add_column("No", style="bold", width=8, no_wrap=True)
    table.add_column("Status", width=6, justify="center")
    table.add_column("Batch", width=6, justify="center")
    table.add_column("Pri", width=5, justify="center")
    table.add_column("Task Name", min_width=30)
    table.add_column("Description", min_width=20, max_width=50)

    for t in tasks:
        status = t.status if hasattr(t, "status") else t.get("status", "not-started")
        icon = STATUS_ICONS.get(status, "❓")
        style = STATUS_STYLES.get(status, "")

        task_no = t.task_no if hasattr(t, "task_no") else t.get("task_no", "?")
        task_name = t.task_name if hasattr(t, "task_name") else t.get("task_name", "")
        batch = str(t.batch if hasattr(t, "batch") else t.get("batch", ""))
        priority = str(t.priority if hasattr(t, "priority") else t.get("priority", ""))
        description = t.description if hasattr(t, "description") else t.get("description", "")
        if len(description) > 50:
            description = description[:47] + "..."

        table.add_row(
            task_no,
            icon,
            batch,
            priority,
            task_name,
            description,
            style=style if status in ("failed",) else "",
        )

    console.print(table)

    total = len(tasks)
    done = sum(
        1 for t in tasks if (t.status if hasattr(t, "status") else t.get("status")) == "completed"
    )
    failed = sum(
        1 for t in tasks if (t.status if hasattr(t, "status") else t.get("status")) == "failed"
    )
    console.print(
        f"\n  [bold]Total:[/bold] {total}  │  "
        f"[green]Done: {done}[/green]  │  "
        f"[red]Failed: {failed}[/red]  │  "
        f"[yellow]Remaining: {total - done}[/yellow]"
    )
    console.print()


# ─── Task Execution Display ─────────────────────────────────────


def show_task_start(idx: int, total: int, task):
    """Display task info panel before execution starts.

    Accepts both v3 Task objects and legacy dicts.
    """
    if hasattr(task, "task_no"):
        # V3 Task object
        task_no = task.task_no
        task_name = task.task_name
        batch = task.batch
        priority = task.priority
        description = task.description
        is_v3 = True
    else:
        # Legacy dict
        task_no = task.get("task_no", f"#{idx + 1}")
        task_name = task.get("task_name", "Unnamed")
        batch = task.get("batch", "?")
        priority = task.get("priority", "?")
        description = task.get("description", "")
        is_v3 = False

    console.rule(
        f"[bold cyan] Task [{idx + 1}/{total}] [/bold cyan]",
        style="cyan",
    )

    if is_v3:
        desc_line = f"  [dim]{description}[/dim]\n" if description else ""
        info = (
            f"  [bold white]{task_no}[/bold white] │ {task_name}\n"
            f"{desc_line}"
            f"  [dim]Batch: {batch}  ·  Priority: {priority}[/dim]"
        )
    else:
        task_type = task.get("type", "?")
        module = task.get("module", "?")
        est = task.get("estimated_minutes", "?")
        info = (
            f"  [bold white]{task_no}[/bold white] │ {task_name}\n"
            f"  [dim]Type: {task_type}  ·  Module: {module}  ·  "
            f"Batch: {batch}  ·  Est: {est}min[/dim]"
        )
    console.print(info)
    console.print()


def show_task_prompt_info(prompt_path: str):
    """Show where the rendered prompt was saved."""
    console.print(f"  [dim]📝 Prompt saved: {prompt_path}[/dim]")


def show_task_cmd(cmd: str):
    """Show the command that will be executed (truncated)."""
    display_cmd = cmd if len(cmd) <= 120 else cmd[:117] + "..."
    console.print(f"  [dim]⚡ Command: {display_cmd}[/dim]")
    console.print()


def show_task_running():
    """Show execution start marker."""
    ts = datetime.now().strftime("%H:%M:%S")
    console.print(f"  [bold green]▶ [{ts}] Executing...[/bold green]")
    console.print(f"  {'─' * 56}")


def show_task_result(
    task_no: str,
    success: bool,
    elapsed: float,
    log_path: str,
    output_tail: str = "",
):
    """Display task result after execution, optionally with AI CLI output tail."""
    time_str = _format_elapsed(elapsed)
    console.print(f"  {'─' * 56}")

    if success:
        console.print(
            f"  [bold green]✅ Task {task_no} completed[/bold green] in [cyan]{time_str}[/cyan]"
        )
    else:
        console.print(f"  [bold red]❌ Task {task_no} failed[/bold red] in [cyan]{time_str}[/cyan]")

    console.print(f"  [dim]📄 Log: {log_path}[/dim]")

    # Show AI CLI output tail so the user can see the actual result
    if output_tail and output_tail.strip():
        show_task_output(task_no, output_tail, success)

    console.print()


# ─── AI CLI Output Summary ───────────────────────────────────────


def show_task_output(task_no: str, output_text: str, success: bool = True, max_lines: int = 25):
    """Display the tail of AI CLI output in a bordered panel.

    This lets the user immediately see what the AI tool actually did/reported
    without having to open the log file.
    """
    lines = output_text.strip().splitlines()
    if not lines:
        return

    # Take the last max_lines
    if len(lines) > max_lines:
        display_lines = [f"  ... ({len(lines) - max_lines} lines omitted)"] + lines[-max_lines:]
    else:
        display_lines = lines

    body = "\n".join(display_lines)

    border_style = "green" if success else "red"
    title = f"📋 Output · {task_no}"

    panel = Panel(
        Text(body, overflow="fold"),
        title=title,
        title_align="left",
        border_style=border_style,
        padding=(0, 1),
        expand=True,
    )
    console.print(panel)


def show_task_skip(task_no: str):
    """Show a skipped (already completed) task."""
    console.print(f"  [dim]⏭️  {task_no} — already completed, skipping[/dim]")


def show_dry_run_skip(task_no: str):
    """Show a dry-run skip."""
    console.print(f"  [yellow]⏭️  DRY-RUN: {task_no} — prompt generated, execution skipped[/yellow]")
    console.print()
