"""Tests for task_runner.commands.run_cmd — multi-task-set support."""

import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from task_runner.commands.run_cmd import _dispatch, _resolve_task_set_names
from task_runner.project import ProjectConfig


# ─── Helpers ───────────────────────────────────────────────────────


def _make_args(**kwargs) -> argparse.Namespace:
    """Build a minimal argparse.Namespace matching CLI expectations."""
    defaults = {
        "project_name": "TEST_PROJECT",
        "task_set_names": [],
        "run_all": False,
        "stop_on_error": False,
        "tool": None,
        "model": None,
        "template": None,
        "proxy_mode": None,
        "batch": None,
        "min_priority": None,
        "start": None,
        "retry_failed": False,
        "work_dir": None,
        "heartbeat": 60,
        "delay": None,
        "timeout": None,
        "git_safety": False,
        "verbose": False,
        "quiet": True,  # suppress banner in tests
        "no_color": True,
        "daemon": False,
        "notify_enabled": False,
        "notify_each": False,
        "wecom_webhook": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project structure for testing."""
    proj = tmp_path / "projects" / "TEST_PROJECT"
    proj.mkdir(parents=True)

    # __init__.json
    config = {
        "project": "TEST_PROJECT",
        "workspace": str(tmp_path),
        "status": "planned",
        "created_at": "2026-01-01_00-00-00",
        "default_tool": "kimi",
        "default_model": "",
        "tags": [],
        "run_record": [],
    }
    (proj / "__init__.json").write_text(json.dumps(config), encoding="utf-8")

    # templates
    tpl_dir = proj / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "__init__.md").write_text("{{task_name}}\n#item\n", encoding="utf-8")

    # runtime
    (proj / "runtime" / "runs").mkdir(parents=True)
    (proj / "runtime" / "backups").mkdir(parents=True)

    # Task sets
    ts_alpha = {"template": "templates/__init__.md", "tasks": [
        {"task_no": "A-1", "task_name": "Alpha task 1", "batch": 1, "priority": 10, "status": "not-started"},
    ]}
    (proj / "alpha.tasks.json").write_text(json.dumps(ts_alpha), encoding="utf-8")

    ts_beta = {"template": "templates/__init__.md", "tasks": [
        {"task_no": "B-1", "task_name": "Beta task 1", "batch": 1, "priority": 10, "status": "not-started"},
    ]}
    (proj / "beta.tasks.json").write_text(json.dumps(ts_beta), encoding="utf-8")

    ts_gamma = {"template": "templates/__init__.md", "tasks": [
        {"task_no": "G-1", "task_name": "Gamma task 1", "batch": 1, "priority": 10, "status": "not-started"},
    ]}
    (proj / "gamma.tasks.json").write_text(json.dumps(ts_gamma), encoding="utf-8")

    return proj


# ─── _resolve_task_set_names ──────────────────────────────────────


class TestResolveTaskSetNames:
    """Test the task set name resolution logic."""

    def test_no_names_and_no_all_returns_none(self):
        args = _make_args()
        result = _resolve_task_set_names(args, "NONEXISTENT")
        assert result is None

    def test_explicit_names_returned_in_order(self, project_dir):
        args = _make_args(task_set_names=["beta", "alpha"])
        with patch("task_runner.commands.run_cmd.get_project_dir", return_value=project_dir):
            result = _resolve_task_set_names(args, "TEST_PROJECT")
        assert result == ["beta", "alpha"]

    def test_nonexistent_name_returns_none(self, project_dir):
        args = _make_args(task_set_names=["alpha", "missing"])
        with patch("task_runner.commands.run_cmd.get_project_dir", return_value=project_dir):
            result = _resolve_task_set_names(args, "TEST_PROJECT")
        assert result is None

    def test_all_returns_alphabetical(self, project_dir):
        args = _make_args(run_all=True)
        config = ProjectConfig(
            project="TEST_PROJECT", workspace=str(project_dir.parent.parent),
            task_set_order=[],
        )
        with (
            patch("task_runner.commands.run_cmd.load_project", return_value=config),
            patch("task_runner.commands.run_cmd.get_project_dir", return_value=project_dir),
        ):
            result = _resolve_task_set_names(args, "TEST_PROJECT")
        assert result == ["alpha", "beta", "gamma"]

    def test_all_with_order_respects_order(self, project_dir):
        args = _make_args(run_all=True)
        config = ProjectConfig(
            project="TEST_PROJECT", workspace=str(project_dir.parent.parent),
            task_set_order=["gamma", "alpha"],
        )
        with (
            patch("task_runner.commands.run_cmd.load_project", return_value=config),
            patch("task_runner.commands.run_cmd.get_project_dir", return_value=project_dir),
        ):
            result = _resolve_task_set_names(args, "TEST_PROJECT")
        # gamma, alpha from order, then beta appended (not in order list)
        assert result == ["gamma", "alpha", "beta"]

    def test_all_with_order_invalid_name_returns_none(self, project_dir):
        args = _make_args(run_all=True)
        config = ProjectConfig(
            project="TEST_PROJECT", workspace=str(project_dir.parent.parent),
            task_set_order=["gamma", "nonexistent"],
        )
        with (
            patch("task_runner.commands.run_cmd.load_project", return_value=config),
            patch("task_runner.commands.run_cmd.get_project_dir", return_value=project_dir),
        ):
            result = _resolve_task_set_names(args, "TEST_PROJECT")
        assert result is None

    def test_all_empty_project_returns_none(self, tmp_path):
        empty_proj = tmp_path / "projects" / "EMPTY"
        empty_proj.mkdir(parents=True)
        config_data = {
            "project": "EMPTY", "workspace": str(tmp_path),
            "status": "planned", "created_at": "2026-01-01_00-00-00",
            "default_tool": "kimi", "default_model": "", "tags": [], "run_record": [],
        }
        (empty_proj / "__init__.json").write_text(json.dumps(config_data), encoding="utf-8")

        args = _make_args(run_all=True, project_name="EMPTY")
        config = ProjectConfig(project="EMPTY", workspace=str(tmp_path), task_set_order=[])
        with (
            patch("task_runner.commands.run_cmd.load_project", return_value=config),
            patch("task_runner.commands.run_cmd.get_project_dir", return_value=empty_proj),
        ):
            result = _resolve_task_set_names(args, "EMPTY")
        assert result is None

    def test_single_name_returned_as_list(self, project_dir):
        args = _make_args(task_set_names=["alpha"])
        with patch("task_runner.commands.run_cmd.get_project_dir", return_value=project_dir):
            result = _resolve_task_set_names(args, "TEST_PROJECT")
        assert result == ["alpha"]


# ─── ProjectConfig.task_set_order ─────────────────────────────────


class TestProjectConfigTaskSetOrder:
    """Test task_set_order field in ProjectConfig."""

    def test_from_dict_reads_order(self):
        data = {
            "project": "X", "workspace": "/tmp", "task_set_order": ["c", "a", "b"],
        }
        config = ProjectConfig.from_dict(data)
        assert config.task_set_order == ["c", "a", "b"]

    def test_from_dict_default_empty(self):
        data = {"project": "X", "workspace": "/tmp"}
        config = ProjectConfig.from_dict(data)
        assert config.task_set_order == []

    def test_to_dict_includes_order_when_set(self):
        config = ProjectConfig(project="X", workspace="/tmp", task_set_order=["a", "b"])
        d = config.to_dict()
        assert d["task_set_order"] == ["a", "b"]

    def test_to_dict_omits_order_when_empty(self):
        config = ProjectConfig(project="X", workspace="/tmp", task_set_order=[])
        d = config.to_dict()
        assert "task_set_order" not in d


# ─── CLI Argument Parsing ─────────────────────────────────────────


class TestCLIParsing:
    """Test that the CLI parser handles multi-task-set args correctly."""

    def test_single_task_set(self):
        from task_runner.cli import parse_args
        args = parse_args(["run", "MY_PROJECT", "fix-bugs"])
        assert args.project_name == "MY_PROJECT"
        assert args.task_set_names == ["fix-bugs"]
        assert args.run_all is False

    def test_multiple_task_sets(self):
        from task_runner.cli import parse_args
        args = parse_args(["run", "MY_PROJECT", "setup", "migration", "cleanup"])
        assert args.task_set_names == ["setup", "migration", "cleanup"]

    def test_all_flag(self):
        from task_runner.cli import parse_args
        args = parse_args(["run", "MY_PROJECT", "--all"])
        assert args.run_all is True
        assert args.task_set_names == []

    def test_stop_on_error_flag(self):
        from task_runner.cli import parse_args
        args = parse_args(["run", "MY_PROJECT", "--all", "--stop-on-error"])
        assert args.stop_on_error is True

    def test_dryrun_multiple_task_sets(self):
        from task_runner.cli import parse_args
        args = parse_args(["dry-run", "MY_PROJECT", "a", "b"])
        assert args.task_set_names == ["a", "b"]

    def test_dryrun_all_flag(self):
        from task_runner.cli import parse_args
        args = parse_args(["dry-run", "MY_PROJECT", "--all"])
        assert args.run_all is True

    def test_no_task_set_no_all_parsed_ok(self):
        """Parser should accept no task sets (validation is in the handler)."""
        from task_runner.cli import parse_args
        args = parse_args(["run", "MY_PROJECT"])
        assert args.task_set_names == []
        assert args.run_all is False


# ─── _dispatch routing ────────────────────────────────────────────


class TestDispatchRouting:
    """Test that _dispatch routes correctly to single vs multi execution."""

    def test_single_calls_execute_single(self, project_dir):
        args = _make_args(task_set_names=["alpha"])
        with (
            patch("task_runner.commands.run_cmd._resolve_task_set_names", return_value=["alpha"]),
            patch("task_runner.commands.run_cmd._execute_single", return_value=0) as mock_single,
        ):
            code = _dispatch(args, dry_run=False)
        assert code == 0
        mock_single.assert_called_once_with(args, "alpha", dry_run=False)

    def test_multi_calls_execute_multi(self, project_dir):
        args = _make_args(task_set_names=["alpha", "beta"])
        with (
            patch("task_runner.commands.run_cmd._resolve_task_set_names", return_value=["alpha", "beta"]),
            patch("task_runner.commands.run_cmd._execute_multi", return_value=0) as mock_multi,
        ):
            code = _dispatch(args, dry_run=False)
        assert code == 0
        mock_multi.assert_called_once_with(args, ["alpha", "beta"], dry_run=False)

    def test_resolve_failure_returns_1(self):
        args = _make_args()
        with patch("task_runner.commands.run_cmd._resolve_task_set_names", return_value=None):
            code = _dispatch(args, dry_run=False)
        assert code == 1


# ─── Multi execution integration ─────────────────────────────────


class TestExecuteMulti:
    """Integration-level tests for multi-task-set execution."""

    def test_stop_on_error_skips_remaining(self):
        from task_runner.commands.run_cmd import _execute_multi

        args = _make_args(
            task_set_names=["alpha", "beta", "gamma"],
            stop_on_error=True,
        )

        call_count = {"n": 0}

        def mock_execute_single(a, name, dry_run=False, _interrupt_flag=None):
            call_count["n"] += 1
            if name == "alpha":
                return 1  # fail
            return 0

        with patch("task_runner.commands.run_cmd._execute_single", side_effect=mock_execute_single):
            code = _execute_multi(args, ["alpha", "beta", "gamma"], dry_run=False)

        assert code == 1
        assert call_count["n"] == 1  # only first set executed

    def test_continue_on_error_by_default(self):
        from task_runner.commands.run_cmd import _execute_multi

        args = _make_args(
            task_set_names=["alpha", "beta", "gamma"],
            stop_on_error=False,
        )

        call_count = {"n": 0}

        def mock_execute_single(a, name, dry_run=False, _interrupt_flag=None):
            call_count["n"] += 1
            if name == "beta":
                return 1  # fail
            return 0

        with patch("task_runner.commands.run_cmd._execute_single", side_effect=mock_execute_single):
            code = _execute_multi(args, ["alpha", "beta", "gamma"], dry_run=False)

        assert code == 1  # overall fails
        assert call_count["n"] == 3  # all sets executed

    def test_all_succeed_returns_0(self):
        from task_runner.commands.run_cmd import _execute_multi

        args = _make_args(stop_on_error=False)

        def mock_execute_single(a, name, dry_run=False, _interrupt_flag=None):
            return 0

        with patch("task_runner.commands.run_cmd._execute_single", side_effect=mock_execute_single):
            code = _execute_multi(args, ["alpha", "beta"], dry_run=False)

        assert code == 0

    def test_interrupt_flag_stops_execution(self):
        from task_runner.commands.run_cmd import _execute_multi

        args = _make_args(stop_on_error=False)
        call_count = {"n": 0}

        def mock_execute_single(a, name, dry_run=False, _interrupt_flag=None):
            call_count["n"] += 1
            if name == "alpha" and _interrupt_flag is not None:
                _interrupt_flag.append(True)
                return 1
            return 0

        with patch("task_runner.commands.run_cmd._execute_single", side_effect=mock_execute_single):
            code = _execute_multi(args, ["alpha", "beta"], dry_run=False)

        assert code == 1
        assert call_count["n"] == 1  # stopped after interrupt

    def test_dry_run_passed_through(self):
        from task_runner.commands.run_cmd import _execute_multi

        args = _make_args(stop_on_error=False)
        dry_run_values = []

        def mock_execute_single(a, name, dry_run=False, _interrupt_flag=None):
            dry_run_values.append(dry_run)
            return 0

        with patch("task_runner.commands.run_cmd._execute_single", side_effect=mock_execute_single):
            _execute_multi(args, ["alpha", "beta"], dry_run=True)

        assert dry_run_values == [True, True]

    def test_daemon_mode_enabled_before_display(self):
        """Daemon flag should trigger enable_daemon_mode before header display."""
        from task_runner.commands.run_cmd import _execute_multi

        args = _make_args(daemon=True, stop_on_error=False)
        daemon_enabled_calls = []

        original_enable = None

        def track_enable():
            daemon_enabled_calls.append(True)

        def mock_execute_single(a, name, dry_run=False, _interrupt_flag=None):
            return 0

        with (
            patch("task_runner.display.enable_daemon_mode", side_effect=track_enable),
            patch("task_runner.display.core.enable_daemon_mode", side_effect=track_enable),
            patch("task_runner.commands.run_cmd._execute_single", side_effect=mock_execute_single),
        ):
            _execute_multi(args, ["alpha"], dry_run=False)

        assert len(daemon_enabled_calls) >= 1

    def test_sigterm_restored_between_task_sets(self):
        """SIGTERM handler should be restored to SIG_DFL after each task set."""
        import signal

        from task_runner.commands.run_cmd import _execute_multi

        args = _make_args(stop_on_error=False)
        sigterm_handlers = []

        def mock_execute_single(a, name, dry_run=False, _interrupt_flag=None):
            return 0

        original_signal = signal.signal

        def tracking_signal(sig, handler):
            if sig == signal.SIGTERM:
                sigterm_handlers.append(handler)
            return original_signal(sig, handler)

        with (
            patch("task_runner.commands.run_cmd._execute_single", side_effect=mock_execute_single),
            patch("task_runner.commands.run_cmd.signal.signal", side_effect=tracking_signal),
        ):
            _execute_multi(args, ["alpha", "beta"], dry_run=False)

        # After each task set, SIGTERM should be restored to SIG_DFL
        assert signal.SIG_DFL in sigterm_handlers
