"""
Project management commands: create, list, info, validate, archive.
"""

from ..display import console, show_error, show_info, show_warning
from ..project import (
    create_project,
    get_project_dir,
    list_projects,
    load_project,
    save_project,
    validate_project,
)
from ..task_set import discover_task_sets, get_task_set_stats, load_task_set


def handle_project(args):
    """Dispatch project subcommands."""
    action = args.project_action

    if action == "create":
        return _project_create(args)
    elif action == "list":
        return _project_list(args)
    elif action == "info":
        return _project_info(args)
    elif action == "validate":
        return _project_validate(args)
    elif action == "archive":
        return _project_archive(args)
    else:
        show_error(f"Unknown project action: {action}")
        return 1


def _project_create(args) -> int:
    """Create a new project."""
    name = args.name
    workspace = args.workspace
    description = getattr(args, "description", "") or ""

    try:
        config = create_project(
            name=name,
            workspace=workspace,
            description=description,
        )
    except FileExistsError:
        show_error(f"Project '{name}' already exists!")
        return 1

    from ..display import show_project_info

    console.print(f"\n[bold green]Project '{name}' created successfully![/bold green]\n")
    show_project_info(config, get_project_dir(name))
    return 0


def _project_list(args) -> int:
    """List all projects."""
    projects = list_projects()

    if not projects:
        show_info(
            "No projects found. Create one with: python run.py project create NAME --workspace PATH"
        )
        return 0

    from ..display import show_project_list

    show_project_list(projects)
    return 0


def _project_info(args) -> int:
    """Show detailed project info."""
    name = args.name

    try:
        config = load_project(name)
    except FileNotFoundError:
        show_error(f"Project '{name}' not found!")
        return 1

    project_dir = get_project_dir(name)

    # Gather task set info
    ts_names = discover_task_sets(project_dir)
    task_sets_info = []
    for ts_name in ts_names:
        try:
            ts = load_task_set(project_dir, ts_name)
            stats = get_task_set_stats(ts)
            task_sets_info.append({"name": ts_name, "stats": stats})
        except Exception:
            task_sets_info.append({"name": ts_name, "stats": None})  # type: ignore[dict-item]

    from ..display import show_project_info

    show_project_info(config, project_dir, task_sets_info)
    return 0


def _project_validate(args) -> int:
    """Validate project structure and data."""
    name = args.name

    from ..display import show_validation_result

    result = validate_project(name)
    show_validation_result(name, result)

    return 0 if result.ok else 1


def _project_archive(args) -> int:
    """Set project status to archived."""
    name = args.name

    try:
        config = load_project(name)
    except FileNotFoundError:
        show_error(f"Project '{name}' not found!")
        return 1

    if config.status == "archived":
        show_warning(f"Project '{name}' is already archived.")
        return 0

    config.status = "archived"
    save_project(config)
    console.print(f"[green]Project '{name}' archived successfully.[/green]")
    return 0
