"""Tests for task_runner.task_set compatibility behavior."""

from task_runner.task_set import Task
from task_runner.validators import validate_task_set_file


def test_task_from_dict_falls_back_to_task_code():
    task = Task.from_dict({"task_code": "JSONEDITOR-001", "task_name": "demo"})
    assert task.task_no == "JSONEDITOR-001"


def test_validate_task_set_accepts_task_code_fallback(tmp_path):
    project_dir = tmp_path
    data = {
        "tasks": [
            {"task_code": "T-001", "task_name": "a", "status": "not-started"},
            {"task_code": "T-002", "task_name": "b", "status": "not-started"},
        ]
    }

    result = validate_task_set_file(data, project_dir)
    assert result.ok
