"""
Validation framework for Auto Task Runner v3.0.

Provides structure, workspace, and data validation for projects and task sets.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    """Collects errors and warnings from validation checks."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def merge(self, other: "ValidationResult"):
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


REQUIRED_INIT_KEYS = {"project", "workspace"}
VALID_PROJECT_STATUSES = {"planned", "active", "completed", "archived"}
VALID_TASK_STATUSES = {"not-started", "in-progress", "completed", "failed", "skipped"}


def validate_init_json(data: dict, project_dir: Path) -> ValidationResult:
    """Validate a project's __init__.json content."""
    result = ValidationResult()

    if not isinstance(data, dict):
        result.add_error("__init__.json must be a JSON object")
        return result

    for key in REQUIRED_INIT_KEYS:
        if key not in data:
            result.add_error(f"Missing required key: '{key}'")

    project_name = data.get("project", "")
    if project_name and project_name != project_dir.name:
        result.add_warning(
            f"Project name '{project_name}' doesn't match directory name '{project_dir.name}'"
        )

    status = data.get("status", "planned")
    if status not in VALID_PROJECT_STATUSES:
        result.add_error(
            f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_PROJECT_STATUSES))}"
        )

    workspace = data.get("workspace", "")
    if workspace and not Path(workspace).is_absolute():
        result.add_error(f"Workspace must be an absolute path, got: '{workspace}'")

    run_record = data.get("run_record", [])
    if not isinstance(run_record, list):
        result.add_error("'run_record' must be a list")

    return result


def validate_workspace(workspace_path: str) -> ValidationResult:
    """Validate that a workspace directory exists and is accessible."""
    result = ValidationResult()

    if not workspace_path:
        result.add_error("Workspace path is empty")
        return result

    ws = Path(workspace_path)
    if not ws.is_absolute():
        result.add_error(f"Workspace must be an absolute path: '{workspace_path}'")
        return result

    if not ws.exists():
        result.add_warning(f"Workspace directory does not exist: '{workspace_path}'")
    elif not ws.is_dir():
        result.add_error(f"Workspace is not a directory: '{workspace_path}'")

    return result


def validate_project_structure(project_dir: Path) -> ValidationResult:
    """Validate the directory structure of a project."""
    result = ValidationResult()

    if not project_dir.exists():
        result.add_error(f"Project directory does not exist: {project_dir}")
        return result

    if not project_dir.is_dir():
        result.add_error(f"Not a directory: {project_dir}")
        return result

    # __init__.json is required
    init_file = project_dir / "__init__.json"
    if not init_file.exists():
        result.add_error(f"Missing required file: __init__.json")
    elif not init_file.is_file():
        result.add_error(f"__init__.json is not a file")

    # templates/ directory should exist with __init__.md
    templates_dir = project_dir / "templates"
    if not templates_dir.exists():
        result.add_warning("Missing 'templates/' directory")
    else:
        default_tpl = templates_dir / "__init__.md"
        if not default_tpl.exists():
            result.add_warning("Missing default template: templates/__init__.md")

    return result


def validate_task_set_file(data: dict, project_dir: Path) -> ValidationResult:
    """Validate the content of a .tasks.json file."""
    result = ValidationResult()

    if not isinstance(data, dict):
        result.add_error("Task set must be a JSON object")
        return result

    tasks = data.get("tasks")
    if tasks is None:
        result.add_error("Missing required key: 'tasks'")
        return result

    if not isinstance(tasks, list):
        result.add_error("'tasks' must be a list")
        return result

    if len(tasks) == 0:
        result.add_warning("Task set has no tasks")
        return result

    seen_nos = set()
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            result.add_error(f"Task [{i}] is not a JSON object")
            continue

        task_no = task.get("task_no")
        if not task_no:
            result.add_error(f"Task [{i}] missing 'task_no'")
        elif task_no in seen_nos:
            result.add_error(f"Duplicate task_no: '{task_no}'")
        else:
            seen_nos.add(task_no)

        if not task.get("task_name"):
            result.add_warning(f"Task [{i}] ('{task_no}') missing 'task_name'")

        status = task.get("status", "not-started")
        if status not in VALID_TASK_STATUSES:
            result.add_error(
                f"Task '{task_no}' has invalid status '{status}'. "
                f"Must be one of: {', '.join(sorted(VALID_TASK_STATUSES))}"
            )

    return result


def validate_template_references(data: dict, project_dir: Path) -> ValidationResult:
    """Validate that template references in a task set resolve to existing files."""
    result = ValidationResult()

    # Check top-level template
    top_template = data.get("template")
    if top_template:
        tpl_path = project_dir / top_template
        if not tpl_path.exists():
            result.add_error(f"Template not found: '{top_template}' (resolved: {tpl_path})")

    # Check per-task prompt/template references
    for task in data.get("tasks", []):
        task_tpl = task.get("prompt") or task.get("template")
        if task_tpl and task_tpl != top_template:
            tpl_path = project_dir / task_tpl
            if not tpl_path.exists():
                result.add_warning(
                    f"Task '{task.get('task_no', '?')}' references missing template: '{task_tpl}'"
                )

    return result
