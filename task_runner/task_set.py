"""
Task set management for Auto Task Runner v3.0.

Handles loading, validation, saving, and default-value resolution for task sets.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from .validators import ValidationResult, validate_task_set_file, validate_template_references


@dataclass
class TaskCLIConfig:
    """Per-task CLI tool/model override."""

    tool: str | None = None
    model: str | None = None

    def to_dict(self) -> dict:
        d = {}
        if self.tool:
            d["tool"] = self.tool
        if self.model:
            d["model"] = self.model
        return d

    @classmethod
    def from_dict(cls, d: dict | None) -> "TaskCLIConfig":
        if not d:
            return cls()
        return cls(tool=d.get("tool"), model=d.get("model"))


@dataclass
class Task:
    """A single task within a task set."""

    task_no: str
    task_name: str = ""
    batch: int = 1
    description: str = ""
    priority: int = 50
    status: str = "not-started"
    prompt: str | None = None  # Per-task template override
    cli: TaskCLIConfig = field(default_factory=TaskCLIConfig)
    depends_on: str | None = None
    _raw: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        """Serialize back to dict, preserving extra fields from _raw."""
        d = dict(self._raw)
        d.update(
            {
                "task_no": self.task_no,
                "task_name": self.task_name,
                "batch": self.batch,
                "description": self.description,
                "priority": self.priority,
                "status": self.status,
            }
        )
        if self.prompt:
            d["prompt"] = self.prompt
        if self.cli.tool or self.cli.model:
            d["cli"] = self.cli.to_dict()
        if self.depends_on:
            d["depends_on"] = self.depends_on
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            task_no=d.get("task_no", ""),
            task_name=d.get("task_name", ""),
            batch=d.get("batch", 1),
            description=d.get("description", ""),
            priority=d.get("priority", 50),
            status=d.get("status", "not-started"),
            prompt=d.get("prompt"),
            cli=TaskCLIConfig.from_dict(d.get("cli")),
            depends_on=d.get("depends_on"),
            _raw=dict(d),
        )


@dataclass
class TaskSet:
    """A collection of tasks loaded from a .tasks.json file."""

    name: str  # Derived from filename (e.g., "code-quality-fix")
    template: str | None = None  # Default template for the set
    tasks: list[Task] = field(default_factory=list)
    _file_path: Path | None = field(default=None, repr=False)
    _raw: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        d = dict(self._raw)
        if self.template:
            d["template"] = self.template
        d["tasks"] = [t.to_dict() for t in self.tasks]
        return d

    @classmethod
    def from_dict(cls, d: dict, name: str, file_path: Path | None = None) -> "TaskSet":
        tasks = [Task.from_dict(t) for t in d.get("tasks", [])]
        return cls(
            name=name,
            template=d.get("template"),
            tasks=tasks,
            _file_path=file_path,
            _raw={k: v for k, v in d.items() if k != "tasks"},
        )


# ─── Discovery & Loading ────────────────────────────────────────


def discover_task_sets(project_dir: Path) -> list[str]:
    """Scan for *.tasks.json files and return their names (without extension)."""
    if not project_dir.exists():
        return []
    return sorted(
        f.stem.replace(".tasks", "") for f in project_dir.glob("*.tasks.json") if f.is_file()
    )


def load_task_set(
    project_dir: Path,
    name: str,
    project_defaults: dict | None = None,
) -> TaskSet:
    """
    Load a task set from disk, validate, and fill in defaults.

    Default resolution chain: task-level > project-level > global defaults.
    """
    file_path = project_dir / f"{name}.tasks.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Task set not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    ts = TaskSet.from_dict(data, name=name, file_path=file_path)

    # Fill defaults from project config
    if project_defaults:
        default_tool = project_defaults.get("default_tool")
        default_model = project_defaults.get("default_model")
        for task in ts.tasks:
            if not task.cli.tool and default_tool:
                task.cli.tool = default_tool
            if not task.cli.model and default_model:
                task.cli.model = default_model

    return ts


def save_task_set(task_set: TaskSet, project_dir: Path | None = None):
    """Persist task set back to its .tasks.json file (atomic write)."""
    if task_set._file_path:
        file_path = task_set._file_path
    elif project_dir:
        file_path = project_dir / f"{task_set.name}.tasks.json"
    else:
        raise ValueError("No file path for task set and no project_dir provided")

    tmp_path = file_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(task_set.to_dict(), f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp_path.replace(file_path)


# ─── Validation ──────────────────────────────────────────────────


def validate_task_set(task_set_path: Path, project_dir: Path) -> ValidationResult:
    """Validate a task set file."""
    result = ValidationResult()
    try:
        with open(task_set_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON: {e}")
        return result

    result.merge(validate_task_set_file(data, project_dir))
    result.merge(validate_template_references(data, project_dir))
    return result


# ─── Statistics ──────────────────────────────────────────────────


def get_task_set_stats(task_set: TaskSet) -> dict:
    """Calculate statistics for a task set."""
    tasks = task_set.tasks
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "completed")
    failed = sum(1 for t in tasks if t.status == "failed")
    in_progress = sum(1 for t in tasks if t.status == "in-progress")
    not_started = total - completed - failed - in_progress

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "in_progress": in_progress,
        "not_started": not_started,
        "remaining": total - completed,
    }
