"""
List command: list task sets and tasks within a project.
"""

from ..display import console, show_error, show_info
from ..project import get_project_dir, load_project
from ..task_set import discover_task_sets, get_task_set_stats, load_task_set


def handle_list(args) -> int:
    """List task sets or tasks."""
    project_name = args.project_name
    task_set_name = getattr(args, "task_set_name", None)
    status_filter = getattr(args, "status", None)

    try:
        load_project(project_name)
    except FileNotFoundError:
        show_error(f"Project '{project_name}' not found!")
        return 1

    project_dir = get_project_dir(project_name)

    if task_set_name:
        return _list_tasks(project_dir, task_set_name, status_filter)
    else:
        return _list_task_sets(project_dir, project_name)


def _list_task_sets(project_dir, project_name: str) -> int:
    """List all task sets in a project."""
    ts_names = discover_task_sets(project_dir)

    if not ts_names:
        show_info(f"No task sets found in project '{project_name}'.")
        show_info("Create a .tasks.json file in the project directory.")
        return 0

    from ..display import show_task_set_list

    sets_info = []
    for name in ts_names:
        try:
            ts = load_task_set(project_dir, name)
            stats = get_task_set_stats(ts)
            sets_info.append({"name": name, "stats": stats, "template": ts.template})
        except Exception as e:
            sets_info.append({"name": name, "stats": None, "error": str(e)})

    show_task_set_list(project_name, sets_info)
    return 0


def _list_tasks(project_dir, task_set_name: str, status_filter: str | None) -> int:
    """List tasks within a specific task set."""
    try:
        ts = load_task_set(project_dir, task_set_name)
    except FileNotFoundError:
        show_error(f"Task set '{task_set_name}' not found!")
        available = discover_task_sets(project_dir)
        if available:
            console.print(f"  [dim]Available: {', '.join(available)}[/dim]")
        return 1

    tasks = ts.tasks
    if status_filter:
        tasks = [t for t in tasks if t.status == status_filter]

    if not tasks:
        show_info(
            "No tasks found" + (f" with status '{status_filter}'" if status_filter else "") + "."
        )
        return 0

    from ..display import show_task_list_v3

    show_task_list_v3(task_set_name, tasks)
    return 0
