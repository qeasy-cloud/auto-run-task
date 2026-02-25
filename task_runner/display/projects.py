"""
Project, task-set, and dashboard display functions.
"""

from rich import box
from rich.panel import Panel
from rich.table import Table

from .core import STATUS_ICONS, STATUS_STYLES, console


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
