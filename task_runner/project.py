"""
Project management for Auto Task Runner v3.0.

Handles project CRUD operations, metadata persistence, and run records.
"""

import contextlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .validators import (
    ValidationResult,
    validate_init_json,
    validate_project_structure,
    validate_task_set_file,
    validate_template_references,
    validate_workspace,
)

# ─── Constants ───────────────────────────────────────────────────

PROJECTS_ROOT = Path(__file__).resolve().parent.parent / "projects"


def get_projects_root() -> Path:
    """Return the root directory for all projects."""
    return PROJECTS_ROOT


def get_project_dir(project_name: str) -> Path:
    """Return the directory for a specific project."""
    return PROJECTS_ROOT / project_name


# ─── Data Classes ────────────────────────────────────────────────


@dataclass
class RunRecord:
    """A single run history entry."""

    run_at: str
    stop_at: str = ""
    cumulated_minutes: float = 0
    status: str = "running"
    task_set_name: str = ""
    tasks_attempted: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0

    def to_dict(self) -> dict:
        return {
            "run_at": self.run_at,
            "stop_at": self.stop_at,
            "cumulated_minutes": self.cumulated_minutes,
            "status": self.status,
            "task_set_name": self.task_set_name,
            "tasks_attempted": self.tasks_attempted,
            "tasks_succeeded": self.tasks_succeeded,
            "tasks_failed": self.tasks_failed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RunRecord":
        return cls(
            run_at=d.get("run_at", ""),
            stop_at=d.get("stop_at", ""),
            cumulated_minutes=d.get("cumulated_minutes", 0),
            status=d.get("status", "running"),
            task_set_name=d.get("task_set_name", ""),
            tasks_attempted=d.get("tasks_attempted", 0),
            tasks_succeeded=d.get("tasks_succeeded", 0),
            tasks_failed=d.get("tasks_failed", 0),
        )


@dataclass
class ProjectConfig:
    """Project metadata loaded from __init__.json."""

    project: str
    workspace: str
    description: str = ""
    status: str = "planned"
    created_at: str = ""
    default_tool: str = "copilot"
    default_model: str = "claude-opus-4.6"
    tags: list[str] = field(default_factory=list)
    run_record: list[RunRecord] = field(default_factory=list)

    # Internal: path to the project directory
    _project_dir: Path | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "description": self.description,
            "workspace": self.workspace,
            "status": self.status,
            "created_at": self.created_at,
            "default_tool": self.default_tool,
            "default_model": self.default_model,
            "tags": self.tags,
            "run_record": [r.to_dict() for r in self.run_record],
        }

    @classmethod
    def from_dict(cls, d: dict, project_dir: Path | None = None) -> "ProjectConfig":
        records = [RunRecord.from_dict(r) for r in d.get("run_record", [])]
        return cls(
            project=d.get("project", ""),
            description=d.get("description", ""),
            workspace=d.get("workspace", ""),
            status=d.get("status", "planned"),
            created_at=d.get("created_at", ""),
            default_tool=d.get("default_tool", "copilot"),
            default_model=d.get("default_model", "claude-opus-4.6"),
            tags=d.get("tags", []),
            run_record=records,
            _project_dir=project_dir,
        )


# ─── CRUD Operations ────────────────────────────────────────────


def create_project(
    name: str,
    workspace: str,
    description: str = "",
    default_tool: str = "copilot",
    default_model: str = "claude-opus-4.6",
    tags: list[str] | None = None,
) -> ProjectConfig:
    """
    Create a new project with scaffolding.

    Creates:
      projects/{name}/
        __init__.json
        templates/
          __init__.md
        runtime/
          runs/
          backups/
    """
    project_dir = get_project_dir(name)
    if project_dir.exists():
        raise FileExistsError(f"Project already exists: {name}")

    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    config = ProjectConfig(
        project=name,
        description=description,
        workspace=workspace,
        status="planned",
        created_at=now_str,
        default_tool=default_tool,
        default_model=default_model,
        tags=tags or [],
        run_record=[],
        _project_dir=project_dir,
    )

    # Create directory structure
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "templates").mkdir(exist_ok=True)
    (project_dir / "runtime" / "runs").mkdir(parents=True, exist_ok=True)
    (project_dir / "runtime" / "backups").mkdir(parents=True, exist_ok=True)

    # Write __init__.json
    save_project(config)

    # Create default template
    default_tpl = project_dir / "templates" / "__init__.md"
    default_tpl.write_text(
        "{{task_name}}\n\n```json\n#item\n```\n",
        encoding="utf-8",
    )

    return config


def load_project(name: str) -> ProjectConfig:
    """Load a project from its __init__.json."""
    project_dir = get_project_dir(name)
    init_file = project_dir / "__init__.json"

    if not init_file.exists():
        raise FileNotFoundError(f"Project not found: {name} (no __init__.json at {init_file})")

    with open(init_file, encoding="utf-8") as f:
        data = json.load(f)

    return ProjectConfig.from_dict(data, project_dir=project_dir)


def save_project(config: ProjectConfig):
    """Persist project config to __init__.json (atomic write)."""
    project_dir = config._project_dir or get_project_dir(config.project)
    init_file = project_dir / "__init__.json"

    tmp_path = init_file.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp_path.replace(init_file)


def list_projects() -> list[ProjectConfig]:
    """List all projects under PROJECTS_ROOT."""
    root = get_projects_root()
    if not root.exists():
        return []

    projects = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "__init__.json").exists():
            with contextlib.suppress(json.JSONDecodeError, KeyError):
                projects.append(load_project(d.name))

    return projects


# ─── Project Operations ─────────────────────────────────────────


def validate_project(name: str) -> ValidationResult:
    """Run full validation on a project."""
    project_dir = get_project_dir(name)
    result = ValidationResult()

    # Structure validation
    result.merge(validate_project_structure(project_dir))
    if not result.ok:
        return result

    # Load and validate __init__.json
    init_file = project_dir / "__init__.json"
    try:
        with open(init_file, encoding="utf-8") as f:
            data = json.load(f)
        result.merge(validate_init_json(data, project_dir))
    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON in __init__.json: {e}")
        return result

    # Validate workspace
    workspace = data.get("workspace", "")
    if workspace:
        result.merge(validate_workspace(workspace))

    # Validate all task set files
    for ts_file in sorted(project_dir.glob("*.tasks.json")):
        try:
            with open(ts_file, encoding="utf-8") as f:
                ts_data = json.load(f)
            ts_result = validate_task_set_file(ts_data, project_dir)
            for err in ts_result.errors:
                result.add_error(f"[{ts_file.name}] {err}")
            for warn in ts_result.warnings:
                result.add_warning(f"[{ts_file.name}] {warn}")

            # Validate template references
            tpl_result = validate_template_references(ts_data, project_dir)
            for err in tpl_result.errors:
                result.add_error(f"[{ts_file.name}] {err}")
            for warn in tpl_result.warnings:
                result.add_warning(f"[{ts_file.name}] {warn}")
        except json.JSONDecodeError as e:
            result.add_error(f"[{ts_file.name}] Invalid JSON: {e}")

    return result


def add_run_record(config: ProjectConfig, record: RunRecord):
    """Add a run record to the project and save."""
    config.run_record.append(record)
    save_project(config)


def update_project_status(config: ProjectConfig, status: str):
    """Update project status and save."""
    config.status = status
    save_project(config)
