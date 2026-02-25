"""
Task plan state management — load, save, and query task plans.

Handles JSON plan persistence with automatic status tracking.
"""

import json
from pathlib import Path


def load_plan(plan_path: Path) -> dict:
    """
    Load a task plan from a JSON file.

    Args:
        plan_path: Absolute path to the plan JSON file.

    Returns:
        The parsed plan dict (must contain a 'tasks' key).

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the plan has no 'tasks' array.
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    if "tasks" not in plan or not isinstance(plan["tasks"], list):
        raise ValueError(f"Plan must contain a 'tasks' array: {plan_path}")

    return plan


def save_plan(plan_path: Path, plan: dict):
    """
    Persist the task plan back to its JSON file (atomic write).

    Uses write-to-temp + rename for crash safety.
    """
    tmp_path = plan_path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp_path.replace(plan_path)


def find_start_index(tasks: list[dict], start_no: str | None) -> int:
    """
    Find the index to start execution from.

    Args:
        tasks: The list of task dicts.
        start_no: If given, find the task with this task_no.
                  If None, find the first non-completed task.

    Returns:
        Index into the tasks list, or -1 if start_no was not found,
        or len(tasks) if all tasks are completed.
    """
    if start_no:
        for i, t in enumerate(tasks):
            if t.get("task_no") == start_no:
                return i
        return -1  # Not found

    # Auto: find first non-completed task
    for i, t in enumerate(tasks):
        if t.get("status") != "completed":
            return i

    return len(tasks)  # All completed


def get_task_stats(tasks: list[dict]) -> dict:
    """
    Calculate task statistics.

    Returns:
        Dict with keys: total, completed, failed, in_progress, not_started, remaining
    """
    total = len(tasks)
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    in_progress = sum(1 for t in tasks if t.get("status") == "in-progress")
    not_started = total - completed - failed - in_progress

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "in_progress": in_progress,
        "not_started": not_started,
        "remaining": total - completed,
    }
