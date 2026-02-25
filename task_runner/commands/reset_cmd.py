"""
Reset command: reset task statuses to allow re-execution.

Supports resetting by status filter, from a specific task onward,
by batch, or all tasks at once.
"""

from ..display import console, show_error, show_info, show_warning
from ..project import get_project_dir, load_project
from ..task_set import load_task_set, save_task_set


def handle_reset(args) -> int:
    """Reset task statuses in a task set."""
    project_name = args.project_name
    task_set_name = args.task_set_name

    # Require at least one selection flag
    has_filter = any([
        args.reset_all,
        args.status,
        args.start_from,
    ])
    if not has_filter:
        show_error(
            "Please specify what to reset:\n"
            "  --all            Reset all tasks\n"
            "  --status failed  Reset tasks with a specific status\n"
            "  --from F-3       Reset tasks from a specific task onward"
        )
        return 1

    # ── Load project & task set ──
    try:
        config = load_project(project_name)
    except FileNotFoundError:
        show_error(f"Project '{project_name}' not found!")
        return 1

    project_dir = get_project_dir(project_name)

    try:
        task_set = load_task_set(
            project_dir,
            task_set_name,
            project_defaults={
                "default_tool": config.default_tool,
                "default_model": config.default_model,
            },
        )
    except FileNotFoundError:
        show_error(f"Task set '{task_set_name}' not found in project '{project_name}'!")
        return 1

    # ── Determine which tasks to reset ──
    targets = list(task_set.tasks)

    # Filter by batch first
    batch_filter = getattr(args, "batch", None)
    if batch_filter is not None:
        targets = [t for t in targets if t.batch == batch_filter]

    if args.status:
        # Only tasks matching the given status
        targets = [t for t in targets if t.status == args.status]

    if args.start_from:
        # From a specific task_no onward (sorted by batch + priority)
        targets.sort(key=lambda t: (t.batch, t.priority))
        found = False
        filtered = []
        for t in targets:
            if t.task_no == args.start_from:
                found = True
            if found:
                filtered.append(t)
        if not found:
            show_error(f"Task '{args.start_from}' not found in task set '{task_set_name}'!")
            return 1
        targets = filtered

    if args.reset_all and not args.status and not args.start_from:
        # --all without other filters: reset everything in targets
        pass  # targets already contains all (possibly batch-filtered)

    # ── Apply reset ──
    if not targets:
        show_info("No tasks match the given criteria.")
        return 0

    reset_count = 0
    already_clean = 0
    for task in targets:
        if task.status == "not-started" and task.elapsed_seconds is None:
            already_clean += 1
            continue
        task.status = "not-started"
        task.elapsed_seconds = None
        task.last_run_at = None
        reset_count += 1

    if reset_count == 0:
        show_info("All matching tasks are already 'not-started'. Nothing to reset.")
        return 0

    # ── Save ──
    save_task_set(task_set, project_dir)

    # ── Report ──
    batch_msg = f" (batch {batch_filter})" if batch_filter else ""
    from_msg = f" from {args.start_from}" if args.start_from else ""
    status_msg = f" with status '{args.status}'" if args.status else ""

    console.print(
        f"\n[bold green]✓ Reset {reset_count} task(s)[/bold green] "
        f"in [cyan]{project_name}/{task_set_name}[/cyan]"
        f"{batch_msg}{status_msg}{from_msg}"
    )

    if already_clean > 0:
        console.print(f"  [dim]({already_clean} task(s) were already 'not-started', skipped)[/dim]")

    console.print(
        f"\n[dim]Run tasks:[/dim] python run.py run {project_name} {task_set_name}"
    )
    if args.start_from:
        console.print(
            f"[dim]Start from:[/dim] python run.py run {project_name} {task_set_name} "
            f"--start {args.start_from}"
        )
    console.print()

    return 0
