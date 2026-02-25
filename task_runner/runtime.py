"""
Runtime directory management for Auto Task Runner v3.0.

Manages per-run directories, metadata, summaries, backups, and symlinks.
"""

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class RunContext:
    """Context for a single execution run."""

    run_id: str
    run_dir: Path
    task_set_name: str
    started_at: str
    tool: str
    model: str | None
    workspace: str
    filters: dict = field(default_factory=dict)
    total_tasks: int = 0
    tasks_to_execute: int = 0

    @property
    def prompts_dir(self) -> Path:
        return self.run_dir / "prompts"

    @property
    def logs_dir(self) -> Path:
        return self.run_dir / "logs"

    def get_prompt_path(self, task_no: str) -> Path:
        safe_name = task_no.replace("/", "_").replace("\\", "_")
        return self.prompts_dir / f"{safe_name}_task.md"

    def get_log_path(self, task_no: str) -> Path:
        safe_name = task_no.replace("/", "_").replace("\\", "_")
        return self.logs_dir / f"{safe_name}.log"


def create_run_context(
    project_dir: Path,
    task_set_name: str,
    tool: str,
    model: str | None,
    workspace: str,
    filters: dict | None = None,
    total_tasks: int = 0,
    tasks_to_execute: int = 0,
) -> RunContext:
    """Create a new run context with a timestamped directory."""
    now = datetime.now()
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_dir_name = f"{run_id}__{task_set_name}"
    run_dir = project_dir / "runtime" / "runs" / run_dir_name

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompts").mkdir(exist_ok=True)
    (run_dir / "logs").mkdir(exist_ok=True)

    ctx = RunContext(
        run_id=run_id,
        run_dir=run_dir,
        task_set_name=task_set_name,
        started_at=now.isoformat(),
        tool=tool,
        model=model,
        workspace=workspace,
        filters=filters or {},
        total_tasks=total_tasks,
        tasks_to_execute=tasks_to_execute,
    )

    return ctx


def save_run_metadata(ctx: RunContext):
    """Write run.json with run metadata."""
    data = {
        "run_id": ctx.run_id,
        "task_set_name": ctx.task_set_name,
        "started_at": ctx.started_at,
        "tool": ctx.tool,
        "model": ctx.model,
        "workspace": ctx.workspace,
        "filters": ctx.filters,
        "total_tasks": ctx.total_tasks,
        "tasks_to_execute": ctx.tasks_to_execute,
    }
    run_json = ctx.run_dir / "run.json"
    with open(run_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def save_run_summary(ctx: RunContext, results: dict, task_results: list[dict]):
    """Write summary.json with execution results."""
    now = datetime.now()
    started = datetime.fromisoformat(ctx.started_at)
    duration = (now - started).total_seconds()

    data = {
        "run_id": ctx.run_id,
        "finished_at": now.isoformat(),
        "duration_seconds": round(duration, 1),
        "status": "completed" if results.get("failed", 0) == 0 else "partial",
        "results": results,
        "tasks": task_results,
    }

    summary_json = ctx.run_dir / "summary.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def backup_task_set(project_dir: Path, task_set_name: str):
    """Backup a task set file to runtime/backups/."""
    src = project_dir / f"{task_set_name}.tasks.json"
    if not src.exists():
        return

    backup_dir = project_dir / "runtime" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dst = backup_dir / f"{task_set_name}_{now_str}.tasks.json"
    shutil.copy2(src, dst)


def update_latest_symlink(project_dir: Path, run_dir: Path):
    """Update the runtime/latest symlink to point to the given run directory."""
    latest = project_dir / "runtime" / "latest"

    # Remove existing symlink or file
    if latest.exists() or latest.is_symlink():
        latest.unlink()

    # Create relative symlink
    try:
        rel_path = os.path.relpath(run_dir, latest.parent)
        latest.symlink_to(rel_path)
    except OSError:
        pass  # Symlinks may not be supported on all platforms


def list_runs(project_dir: Path) -> list[dict]:
    """List all runs for a project, sorted by time (newest first)."""
    runs_dir = project_dir / "runtime" / "runs"
    if not runs_dir.exists():
        return []

    results = []
    for d in sorted(runs_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        run_json = d / "run.json"
        if run_json.exists():
            try:
                with open(run_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Augment with summary if available
                summary_json = d / "summary.json"
                if summary_json.exists():
                    with open(summary_json, "r", encoding="utf-8") as f:
                        summary = json.load(f)
                    data["summary"] = summary
                results.append(data)
            except (json.JSONDecodeError, KeyError):
                pass

    return results
