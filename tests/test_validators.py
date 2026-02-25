"""Tests for task_runner.validators module."""

from pathlib import Path

import pytest

from task_runner.validators import (
    VALID_PROJECT_STATUSES,
    VALID_TASK_STATUSES,
    ValidationResult,
    validate_init_json,
    validate_workspace,
)


class TestValidationResult:
    def test_ok_when_no_errors(self):
        r = ValidationResult()
        assert r.ok is True

    def test_not_ok_with_errors(self):
        r = ValidationResult()
        r.add_error("bad thing")
        assert r.ok is False

    def test_add_warning_does_not_break_ok(self):
        r = ValidationResult()
        r.add_warning("minor concern")
        assert r.ok is True
        assert len(r.warnings) == 1

    def test_merge_combines_errors_and_warnings(self):
        a = ValidationResult()
        a.add_error("error-a")
        a.add_warning("warn-a")

        b = ValidationResult()
        b.add_error("error-b")
        b.add_warning("warn-b")

        a.merge(b)
        assert len(a.errors) == 2
        assert len(a.warnings) == 2
        assert "error-b" in a.errors
        assert "warn-b" in a.warnings

    def test_merge_empty_result(self):
        a = ValidationResult()
        a.add_error("existing")
        a.merge(ValidationResult())
        assert len(a.errors) == 1


class TestValidateInitJson:
    def _dir(self, tmp_path: Path, name: str = "MY_PROJECT") -> Path:
        d = tmp_path / name
        d.mkdir()
        return d

    def test_valid_data_passes(self, tmp_path):
        project_dir = self._dir(tmp_path, "MY_PROJECT")
        data = {"project": "MY_PROJECT", "workspace": "/some/abs/path"}
        result = validate_init_json(data, project_dir)
        assert result.ok

    def test_missing_project_key(self, tmp_path):
        project_dir = self._dir(tmp_path)
        data = {"workspace": "/some/path"}
        result = validate_init_json(data, project_dir)
        assert not result.ok
        assert any("project" in e for e in result.errors)

    def test_missing_workspace_key(self, tmp_path):
        project_dir = self._dir(tmp_path)
        data = {"project": "MY_PROJECT"}
        result = validate_init_json(data, project_dir)
        assert not result.ok
        assert any("workspace" in e for e in result.errors)

    def test_invalid_status_error(self, tmp_path):
        project_dir = self._dir(tmp_path, "P")
        data = {"project": "P", "workspace": "/abs", "status": "unknown_status"}
        result = validate_init_json(data, project_dir)
        assert not result.ok
        assert any("status" in e.lower() for e in result.errors)

    @pytest.mark.parametrize("status", sorted(VALID_PROJECT_STATUSES))
    def test_all_valid_statuses_accepted(self, tmp_path, status):
        project_dir = self._dir(tmp_path, "P")
        data = {"project": "P", "workspace": "/abs", "status": status}
        result = validate_init_json(data, project_dir)
        status_errors = [e for e in result.errors if "status" in e.lower()]
        assert len(status_errors) == 0

    def test_relative_workspace_is_error(self, tmp_path):
        project_dir = self._dir(tmp_path, "P")
        data = {"project": "P", "workspace": "relative/path"}
        result = validate_init_json(data, project_dir)
        assert not result.ok
        assert any("absolute" in e.lower() for e in result.errors)

    def test_name_mismatch_is_warning(self, tmp_path):
        project_dir = self._dir(tmp_path, "ACTUAL_NAME")
        data = {"project": "DIFFERENT_NAME", "workspace": "/abs"}
        result = validate_init_json(data, project_dir)
        # Should be a warning, not an error (still ok)
        assert result.ok
        assert len(result.warnings) > 0

    def test_non_dict_input_returns_error(self, tmp_path):
        project_dir = self._dir(tmp_path)
        result = validate_init_json(["not", "a", "dict"], project_dir)  # type: ignore[arg-type]
        assert not result.ok

    def test_run_record_must_be_list(self, tmp_path):
        project_dir = self._dir(tmp_path, "P")
        data = {"project": "P", "workspace": "/abs", "run_record": "not-a-list"}
        result = validate_init_json(data, project_dir)
        assert not result.ok


class TestValidateWorkspace:
    def test_valid_existing_directory(self, tmp_path):
        result = validate_workspace(str(tmp_path))
        assert result.ok

    def test_empty_path_is_error(self):
        result = validate_workspace("")
        assert not result.ok

    def test_relative_path_is_error(self):
        result = validate_workspace("relative/dir")
        assert not result.ok

    def test_nonexistent_path_is_warning(self, tmp_path):
        missing = str(tmp_path / "does_not_exist")
        result = validate_workspace(missing)
        # Directory doesn't exist → warning, not error
        assert result.ok
        assert len(result.warnings) > 0

    def test_file_path_is_error(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        result = validate_workspace(str(f))
        assert not result.ok


class TestValidTaskStatuses:
    def test_expected_statuses_present(self):
        assert "not-started" in VALID_TASK_STATUSES
        assert "in-progress" in VALID_TASK_STATUSES
        assert "completed" in VALID_TASK_STATUSES
        assert "failed" in VALID_TASK_STATUSES
        assert "skipped" in VALID_TASK_STATUSES
