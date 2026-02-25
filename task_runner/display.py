"""
Rich terminal display helpers for Auto Task Runner v3.0.

Provides all visual output: banners, tables, task panels, heartbeat,
progress indicators, execution summaries, project dashboards, and validation.
"""

import sys
from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ─── Singleton Console ───────────────────────────────────────────

console = Console(highlight=False)

# ─── Constants ───────────────────────────────────────────────────

STATUS_ICONS = {
    "not-started": "⬜",
    "in-progress": "🔄",
    "completed": "✅",
    "failed": "❌",
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


# ─── Banner (Legacy) ────────────────────────────────────────────


def show_banner(
    project: str,
    tool: str,
    model: str | None,
    plan_path: str,
    template_path: str,
    total: int,
    done: int,
    remaining: int,
    use_proxy: bool,
    work_dir: str,
):
    """Display the startup banner with full configuration info (legacy mode)."""
    console.print(Text(LOGO, style="bold cyan"), highlight=False)

    tool_str = f"[green]{tool}[/green]"
    if model:
        tool_str += f"  [dim]model:[/dim] [yellow]{model}[/yellow]"

    proxy_str = "[green]✓ enabled[/green]" if use_proxy else "[dim]✗ disabled[/dim]"

    info_lines = [
        f"[bold]Project[/bold]    │ [cyan]{project}[/cyan]",
        f"[bold]Tool[/bold]       │ {tool_str}",
        f"[bold]Plan[/bold]       │ {plan_path}",
        f"[bold]Template[/bold]   │ {template_path}",
        f"[bold]Work Dir[/bold]   │ {work_dir}",
        f"[bold]Tasks[/bold]      │ {total} total  ·  [green]{done} done[/green] "
        f" ·  [yellow]{remaining} remaining[/yellow]",
        f"[bold]Proxy[/bold]      │ {proxy_str}",
        f"[bold]Started[/bold]    │ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    panel = Panel(
        "\n".join(info_lines),
        title="[bold] 🚀 Auto Task Runner [/bold]",
        subtitle="[dim]CTRL+C to stop gracefully[/dim]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


# ─── Banner (V3) ────────────────────────────────────────────────


def show_banner_v3(
    project: str,
    task_set: str,
    tool: str,
    model: str | None,
    workspace: str,
    run_id: str,
    total: int,
    done: int,
    remaining: int,
    to_execute: int,
    use_proxy: bool,
):
    """Display the v3 startup banner."""
    console.print(Text(LOGO, style="bold cyan"), highlight=False)

    tool_str = f"[green]{tool}[/green]"
    if model:
        tool_str += f"  [dim]model:[/dim] [yellow]{model}[/yellow]"

    proxy_str = "[green]✓ enabled[/green]" if use_proxy else "[dim]✗ disabled[/dim]"

    info_lines = [
        f"[bold]Project[/bold]    │ [cyan]{project}[/cyan]",
        f"[bold]Task Set[/bold]   │ [magenta]{task_set}[/magenta]",
        f"[bold]Tool[/bold]       │ {tool_str}",
        f"[bold]Workspace[/bold]  │ {workspace}",
        f"[bold]Run ID[/bold]     │ [dim]{run_id}[/dim]",
        f"[bold]Tasks[/bold]      │ {total} total  ·  [green]{done} done[/green] "
        f" ·  [yellow]{remaining} remaining[/yellow]  ·  [cyan]{to_execute} to execute[/cyan]",
        f"[bold]Proxy[/bold]      │ {proxy_str}",
        f"[bold]Started[/bold]    │ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    panel = Panel(
        "\n".join(info_lines),
        title="[bold] 🚀 Auto Task Runner v3.0 [/bold]",
        subtitle="[dim]CTRL+C to stop gracefully[/dim]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


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


def show_task_start(idx: int, total: int, task: dict):
    """Display task info panel before execution starts."""
    task_no = task.get("task_no", f"#{idx + 1}")
    task_name = task.get("task_name", "Unnamed")
    task_type = task.get("type", "?")
    module = task.get("module", "?")
    est = task.get("estimated_minutes", "?")
    batch = task.get("batch", "?")

    console.rule(
        f"[bold cyan] Task [{idx + 1}/{total}] [/bold cyan]",
        style="cyan",
    )

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


def show_task_result(task_no: str, success: bool, elapsed: float, log_path: str):
    """Display task result after execution."""
    time_str = _format_elapsed(elapsed)
    console.print(f"  {'─' * 56}")

    if success:
        console.print(
            f"  [bold green]✅ Task {task_no} completed[/bold green] in [cyan]{time_str}[/cyan]"
        )
    else:
        console.print(f"  [bold red]❌ Task {task_no} failed[/bold red] in [cyan]{time_str}[/cyan]")

    console.print(f"  [dim]📄 Log: {log_path}[/dim]")
    console.print()


def show_task_skip(task_no: str):
    """Show a skipped (already completed) task."""
    console.print(f"  [dim]⏭️  {task_no} — already completed, skipping[/dim]")


def show_dry_run_skip(task_no: str):
    """Show a dry-run skip."""
    console.print(f"  [yellow]⏭️  DRY-RUN: {task_no} — prompt generated, execution skipped[/yellow]")
    console.print()


# ─── Heartbeat ───────────────────────────────────────────────────


def show_heartbeat(task_no: str, elapsed: float, frame_idx: int = 0):
    """Print a heartbeat line during long-running tasks."""
    time_str = _format_elapsed(elapsed)
    spinner = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
    ts = datetime.now().strftime("%H:%M:%S")

    console.print(f"  [dim]{spinner} [{ts}] Task {task_no} running... ({time_str} elapsed)[/dim]")


# ─── Summary ─────────────────────────────────────────────────────


def show_summary(
    succeeded: int,
    failed: int,
    skipped: int,
    total: int,
    total_done: int,
    total_elapsed: float,
    interrupted: bool,
):
    """Display the final execution summary panel."""
    time_str = _format_elapsed(total_elapsed)

    if interrupted:
        title = "⚠️  [bold yellow]Execution Interrupted[/bold yellow]"
        border = "yellow"
    elif failed > 0:
        title = "📊 [bold]Execution Summary[/bold]"
        border = "red"
    else:
        title = "🎉 [bold green]All Tasks Completed![/bold green]"
        border = "green"

    lines = [
        f"[green]✅ Succeeded[/green]   │ {succeeded}",
        f"[red]❌ Failed[/red]      │ {failed}",
        f"[dim]⏭️  Skipped[/dim]     │ {skipped}",
        "",
        f"[bold]📊 Total Done[/bold]  │ {total_done} / {total}",
        f"[cyan]⏱  Duration[/cyan]   │ {time_str}",
    ]

    panel = Panel(
        "\n".join(lines),
        title=title,
        border_style=border,
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def show_all_done():
    """Display a message when all tasks are already completed."""
    console.print(
        Panel(
            "[bold green]🎉 All tasks have already been completed![/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


# ─── Project Display (V3) ───────────────────────────────────────


def show_project_list(projects: list):
    """Display a table of all projects."""
    table = Table(
        title="📁 Projects",
        box=box.ROUNDED,
        show_lines=False,
        title_style="bold",
        header_style="bold bright_blue",
    )

    table.add_column("Name", style="bold cyan", min_width=15)
    table.add_column("Status", width=10, justify="center")
    table.add_column("Workspace", min_width=30)
    table.add_column("Description", min_width=20, max_width=40)
    table.add_column("Tool", width=10)
    table.add_column("Runs", width=5, justify="right")

    for p in projects:
        status = p.status
        icon = STATUS_ICONS.get(status, "❓")
        style = STATUS_STYLES.get(status, "")

        desc = p.description
        if len(desc) > 40:
            desc = desc[:37] + "..."

        table.add_row(
            p.project,
            f"{icon} {status}",
            p.workspace,
            desc,
            p.default_tool,
            str(len(p.run_record)),
            style=style if status == "archived" else "",
        )

    console.print(table)
    console.print(f"\n  [dim]Total: {len(projects)} projects[/dim]\n")


def show_project_info(config, project_dir, task_sets_info: list | None = None):
    """Display detailed project information panel."""
    status = config.status
    icon = STATUS_ICONS.get(status, "❓")

    info_lines = [
        f"[bold]Project[/bold]      │ [cyan]{config.project}[/cyan]",
        f"[bold]Description[/bold]  │ {config.description or '(none)'}",
        f"[bold]Status[/bold]       │ {icon} {status}",
        f"[bold]Workspace[/bold]    │ {config.workspace}",
        f"[bold]Tool[/bold]         │ {config.default_tool}  [dim]model:[/dim] {config.default_model}",
        f"[bold]Created[/bold]      │ {config.created_at}",
    ]

    if config.tags:
        info_lines.append(f"[bold]Tags[/bold]         │ {', '.join(config.tags)}")

    info_lines.append(f"[bold]Runs[/bold]         │ {len(config.run_record)}")

    panel = Panel(
        "\n".join(info_lines),
        title=f"[bold] 📁 Project: {config.project} [/bold]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )
    console.print(panel)

    # Task sets
    if task_sets_info:
        console.print()
        table = Table(
            title="Task Sets",
            box=box.SIMPLE,
            header_style="bold",
        )
        table.add_column("Name", style="magenta")
        table.add_column("Total", justify="right")
        table.add_column("Done", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Remaining", justify="right", style="yellow")

        for ts in task_sets_info:
            stats = ts.get("stats")
            if stats:
                table.add_row(
                    ts["name"],
                    str(stats["total"]),
                    str(stats["completed"]),
                    str(stats["failed"]),
                    str(stats["remaining"]),
                )
            else:
                table.add_row(ts["name"], "?", "?", "?", "?")

        console.print(table)

    console.print()


def show_task_set_list(project_name: str, sets_info: list):
    """Display a table of task sets in a project."""
    table = Table(
        title=f"📋 Task Sets in '{project_name}'",
        box=box.ROUNDED,
        show_lines=False,
        title_style="bold",
        header_style="bold bright_blue",
    )

    table.add_column("Name", style="magenta", min_width=20)
    table.add_column("Template", min_width=20)
    table.add_column("Total", width=6, justify="right")
    table.add_column("Done", width=6, justify="right", style="green")
    table.add_column("Failed", width=7, justify="right", style="red")
    table.add_column("Remaining", width=10, justify="right", style="yellow")

    for info in sets_info:
        stats = info.get("stats")
        template = info.get("template", "")
        if stats:
            table.add_row(
                info["name"],
                template or "(default)",
                str(stats["total"]),
                str(stats["completed"]),
                str(stats["failed"]),
                str(stats["remaining"]),
            )
        else:
            error = info.get("error", "load error")
            table.add_row(info["name"], f"[red]{error}[/red]", "?", "?", "?", "?")

    console.print(table)
    console.print()


def show_validation_result(name: str, result):
    """Display validation errors and warnings with color."""
    if result.ok and not result.warnings:
        console.print(f"\n[bold green]✅ Project '{name}' validation passed![/bold green]\n")
        return

    if result.errors:
        console.print(f"\n[bold red]❌ Validation errors for '{name}':[/bold red]")
        for err in result.errors:
            console.print(f"  [red]  • {err}[/red]")

    if result.warnings:
        console.print(f"\n[yellow]⚠️  Warnings for '{name}':[/yellow]")
        for warn in result.warnings:
            console.print(f"  [yellow]  • {warn}[/yellow]")

    console.print()

    if result.ok:
        console.print(f"  [green]Result: PASS (with {len(result.warnings)} warnings)[/green]\n")
    else:
        console.print(
            f"  [red]Result: FAIL ({len(result.errors)} errors, {len(result.warnings)} warnings)[/red]\n"
        )


def show_run_history(runs: list[dict]):
    """Display run history table."""
    table = Table(
        title="📜 Run History",
        box=box.SIMPLE,
        header_style="bold",
    )

    table.add_column("Run ID", style="dim")
    table.add_column("Task Set", style="magenta")
    table.add_column("Tool", width=10)
    table.add_column("Tasks", width=6, justify="right")
    table.add_column("Status", width=12)

    for run in runs[:10]:  # Show last 10
        status = run.get("summary", {}).get("status", "unknown")
        icon = STATUS_ICONS.get(status, "❓")

        summary = run.get("summary", {})
        results = summary.get("results", {})
        tasks_info = f"{results.get('succeeded', '?')}/{run.get('total_tasks', '?')}"

        table.add_row(
            run.get("run_id", "?"),
            run.get("task_set_name", "?"),
            run.get("tool", "?"),
            tasks_info,
            f"{icon} {status}",
        )

    console.print(table)
    console.print()


def show_project_dashboard(dashboard_data: list[dict]):
    """Display multi-project dashboard."""
    table = Table(
        title="🎯 Project Dashboard",
        box=box.DOUBLE_EDGE,
        show_lines=True,
        title_style="bold",
        header_style="bold bright_blue",
    )

    table.add_column("Project", style="bold cyan", min_width=15)
    table.add_column("Status", width=12, justify="center")
    table.add_column("Task Sets", width=10, justify="center")
    table.add_column("Progress", min_width=20)
    table.add_column("Failed", width=7, justify="center")
    table.add_column("Last Run", width=20)

    for item in dashboard_data:
        config = item["config"]
        status = config.status
        icon = STATUS_ICONS.get(status, "❓")

        total = item["total_tasks"]
        completed = item["completed_tasks"]
        failed_count = item["failed_tasks"]

        if total > 0:
            pct = completed / total * 100
            bar_width = 10
            filled = int(bar_width * completed / total)
            bar = "█" * filled + "░" * (bar_width - filled)
            progress = f"{bar} {completed}/{total} ({pct:.0f}%)"
        else:
            progress = "[dim]no tasks[/dim]"

        last_run = item.get("last_run")
        last_run_str = last_run.get("run_id", "?") if last_run else "[dim]never[/dim]"

        failed_str = f"[red]{failed_count}[/red]" if failed_count > 0 else "[dim]0[/dim]"

        table.add_row(
            config.project,
            f"{icon} {status}",
            str(item["task_sets"]),
            progress,
            failed_str,
            last_run_str,
        )

    console.print(table)
    console.print()


def show_schedule_plan(waves: list[list]):
    """Display the execution plan with batch/priority arrangement."""
    for i, wave in enumerate(waves, 1):
        console.print(f"\n  [bold cyan]Wave {i}[/bold cyan] ({len(wave)} tasks):")
        for task in wave:
            task_no = task.task_no if hasattr(task, "task_no") else task.get("task_no", "?")
            task_name = task.task_name if hasattr(task, "task_name") else task.get("task_name", "")
            batch = task.batch if hasattr(task, "batch") else task.get("batch", "?")
            priority = task.priority if hasattr(task, "priority") else task.get("priority", "?")
            console.print(f"    [dim]B{batch}/P{priority}[/dim]  {task_no} — {task_name}")
    console.print()


# ─── Utility Messages ───────────────────────────────────────────


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


# ─── Progress Bar ────────────────────────────────────────────────


def show_progress_bar(current: int, total: int, width: int = 40):
    """Display a simple text-based progress bar."""
    if total == 0:
        return
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = current / total * 100
    console.print(
        f"  [cyan]Progress[/cyan] │[bold green]{bar}[/bold green]│ "
        f"[bold]{current}/{total}[/bold] ({pct:.0f}%)"
    )
    console.print()


# ─── Internal Helpers ────────────────────────────────────────────


def _format_elapsed(elapsed: float) -> str:
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
