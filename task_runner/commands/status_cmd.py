"""
Status command: project dashboard and per-project status.
"""

from ..display import show_error, show_info
from ..project import get_project_dir, list_projects, load_project
from ..runtime import list_runs
from ..task_set import discover_task_sets, get_task_set_stats, load_task_set


def handle_status(args) -> int:
    """Show status dashboard."""
    project_name = getattr(args, "project_name", None)

    if project_name:
        return _project_status(project_name)
    else:
        return _dashboard()


def _dashboard() -> int:
    """Show multi-project dashboard."""
    projects = list_projects()

    if not projects:
        show_info(
            "No projects found. Create one with: python run.py project create NAME --workspace PATH"
        )
        return 0

    # Gather stats for each project
    dashboard_data = []
    for config in projects:
        project_dir = get_project_dir(config.project)
        ts_names = discover_task_sets(project_dir)

        total_tasks = 0
        completed_tasks = 0
        failed_tasks = 0

        for ts_name in ts_names:
            try:
                ts = load_task_set(project_dir, ts_name)
                stats = get_task_set_stats(ts)
                total_tasks += stats["total"]
                completed_tasks += stats["completed"]
                failed_tasks += stats["failed"]
            except Exception:
                pass

        runs = list_runs(project_dir)
        last_run = runs[0] if runs else None

        dashboard_data.append(
            {
                "config": config,
                "task_sets": len(ts_names),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "last_run": last_run,
            }
        )

    from ..display import show_project_dashboard

    show_project_dashboard(dashboard_data)
    return 0


def _project_status(project_name: str) -> int:
    """Show single project detailed status."""
    try:
        config = load_project(project_name)
    except FileNotFoundError:
        show_error(f"Project '{project_name}' not found!")
        return 1

    project_dir = get_project_dir(project_name)

    # Task set details
    ts_names = discover_task_sets(project_dir)
    task_sets_info = []
    for ts_name in ts_names:
        try:
            ts = load_task_set(project_dir, ts_name)
            stats = get_task_set_stats(ts)
            task_sets_info.append({"name": ts_name, "stats": stats})
        except Exception as e:
            task_sets_info.append({"name": ts_name, "stats": None, "error": str(e)})  # type: ignore[dict-item]

    # Run history
    runs = list_runs(project_dir)

    from ..display import show_project_info, show_run_history

    show_project_info(config, project_dir, task_sets_info)
    if runs:
        show_run_history(runs)

    return 0
