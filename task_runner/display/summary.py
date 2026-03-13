"""
Execution summary and progress bar display.
"""

from rich import box
from rich.panel import Panel
from rich.table import Table

from .core import STATUS_ICONS, _format_elapsed, console


def show_multi_task_set_header(task_set_names: list[str], project: str):
    """Display header for multi-task-set sequential execution."""
    names_str = ", ".join(f"[magenta]{n}[/magenta]" for n in task_set_names)
    panel = Panel(
        f"[bold]Project:[/bold] [cyan]{project}[/cyan]\n"
        f"[bold]Task Sets ({len(task_set_names)}):[/bold] {names_str}\n"
        f"[bold]Mode:[/bold] Sequential execution",
        title="[bold] 📋 Multi Task Set Execution [/bold]",
        border_style="bright_blue",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def show_task_set_divider(current: int, total: int, name: str):
    """Display a separator between task sets in multi-mode."""
    console.print()
    console.rule(
        f"[bold cyan]📦 Task Set [{current}/{total}]: {name}[/bold cyan]",
        style="bright_blue",
    )
    console.print()


def show_multi_task_set_summary(
    results: list[dict],
    total_elapsed: float,
    interrupted: bool = False,
):
    """Display combined summary for multi-task-set execution."""
    all_succeeded = all(r["code"] == 0 for r in results)

    if interrupted:
        title = "⚠️  [bold yellow]Multi Task Set Execution Interrupted[/bold yellow]"
        border = "yellow"
    elif all_succeeded:
        title = "🎉 [bold green]All Task Sets Completed Successfully![/bold green]"
        border = "green"
    else:
        title = "📊 [bold]Multi Task Set Execution Summary[/bold]"
        border = "red"

    # Per task set table
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold",
        padding=(0, 1),
    )
    table.add_column("#", width=4, justify="center")
    table.add_column("Task Set", style="bold", min_width=15)
    table.add_column("Status", width=10, justify="center")
    table.add_column("Duration", width=12, justify="right", style="cyan")

    sets_ok = 0
    sets_fail = 0
    for i, r in enumerate(results, 1):
        ok = r["code"] == 0
        icon = "✅" if ok else "❌"
        if ok:
            sets_ok += 1
        else:
            sets_fail += 1
        table.add_row(
            str(i),
            r["task_set_name"],
            icon,
            _format_elapsed(r["elapsed"]),
        )

    console.print()
    console.rule("[bold]Multi Task Set Summary[/bold]", style="bright_blue")
    console.print()
    console.print(table)

    # Overall stats
    lines = [
        f"[green]✅ Succeeded[/green]   │ {sets_ok} task set(s)",
        f"[red]❌ Failed[/red]      │ {sets_fail} task set(s)",
        f"[cyan]⏱  Duration[/cyan]   │ {_format_elapsed(total_elapsed)}",
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


def show_summary(
    succeeded: int,
    failed: int,
    skipped: int,
    total: int,
    total_done: int,
    total_elapsed: float,
    interrupted: bool,
    task_results: list[dict] | None = None,
):
    """Display the final execution summary panel with optional per-task table."""
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

    # ── Per-task timing table ──
    if task_results:
        task_table = Table(
            box=box.SIMPLE_HEAVY,
            show_header=True,
            header_style="bold",
            padding=(0, 1),
        )
        task_table.add_column("Task", style="bold", min_width=10)
        task_table.add_column("Status", width=8, justify="center")
        task_table.add_column("Duration", width=10, justify="right", style="cyan")
        task_table.add_column("Exit", width=5, justify="center")

        for r in task_results:
            status = r.get("status", "?")
            icon = STATUS_ICONS.get(status, "❓")
            dur = _format_elapsed(r.get("duration_seconds", 0))
            rc = str(r.get("return_code", "?"))
            rc_style = "[green]" if rc == "0" else "[red]"

            task_table.add_row(
                r.get("task_no", "?"),
                icon,
                dur,
                f"{rc_style}{rc}[/]",
            )

        console.print()
        console.print(task_table)

    # ── Summary stats ──
    pct = (total_done / total * 100) if total > 0 else 0
    bar_width = 20
    filled = int(bar_width * total_done / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_width - filled)

    lines = [
        f"[green]✅ Succeeded[/green]   │ {succeeded}",
        f"[red]❌ Failed[/red]      │ {failed}",
        f"[dim]⏭️  Skipped[/dim]     │ {skipped}",
        "",
        f"[bold]📊 Progress[/bold]    │ [green]{bar}[/green] {total_done}/{total} ({pct:.0f}%)",
        f"[cyan]⏱  Duration[/cyan]   │ {time_str}",
    ]

    if task_results:
        durations = [
            r.get("duration_seconds", 0) for r in task_results if r.get("duration_seconds")
        ]
        if durations:
            avg = sum(durations) / len(durations)
            lines.append(f"[dim]📈 Avg/Task[/dim]   │ {_format_elapsed(avg)}")

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
