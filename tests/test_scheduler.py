"""Tests for task_runner.scheduler module."""

from task_runner.scheduler import (
    get_execution_plan,
    schedule_tasks,
    validate_dependencies,
)
from task_runner.task_set import Task, TaskCLIConfig, TaskSet

# ─── Helpers ───────────────────────────────────────────────────────


def _make_task(
    task_no: str,
    batch: int = 1,
    priority: int = 50,
    status: str = "not-started",
    depends_on: str | None = None,
) -> Task:
    return Task(
        task_no=task_no,
        task_name=f"Task {task_no}",
        batch=batch,
        priority=priority,
        status=status,
        depends_on=depends_on,
        cli=TaskCLIConfig(),
    )


def _make_task_set(tasks: list[Task]) -> TaskSet:
    return TaskSet(name="test-set", tasks=tasks)


# ─── schedule_tasks ────────────────────────────────────────────────


class TestScheduleTasks:
    def test_returns_all_tasks_by_default(self):
        ts = _make_task_set([_make_task("T-1"), _make_task("T-2"), _make_task("T-3")])
        result = schedule_tasks(ts)
        assert [t.task_no for t in result] == ["T-1", "T-2", "T-3"]

    def test_sorts_by_batch_then_priority(self):
        tasks = [
            _make_task("T-3", batch=1, priority=20),
            _make_task("T-1", batch=1, priority=10),
            _make_task("T-4", batch=2, priority=5),
            _make_task("T-2", batch=1, priority=15),
        ]
        ts = _make_task_set(tasks)
        result = schedule_tasks(ts)
        assert [t.task_no for t in result] == ["T-1", "T-2", "T-3", "T-4"]

    def test_filter_by_batch(self):
        tasks = [_make_task("A", batch=1), _make_task("B", batch=2), _make_task("C", batch=1)]
        ts = _make_task_set(tasks)
        result = schedule_tasks(ts, batch=1)
        assert all(t.batch == 1 for t in result)
        assert len(result) == 2

    def test_filter_by_status(self):
        tasks = [
            _make_task("T-1", status="completed"),
            _make_task("T-2", status="failed"),
            _make_task("T-3", status="not-started"),
        ]
        ts = _make_task_set(tasks)
        result = schedule_tasks(ts, status_filter="failed")
        assert len(result) == 1
        assert result[0].task_no == "T-2"

    def test_retry_failed_only(self):
        tasks = [
            _make_task("T-1", status="failed"),
            _make_task("T-2", status="completed"),
            _make_task("T-3", status="failed"),
        ]
        ts = _make_task_set(tasks)
        result = schedule_tasks(ts, retry_failed=True)
        assert all(t.status == "failed" for t in result)
        assert len(result) == 2

    def test_start_from_existing_task(self):
        tasks = [_make_task(f"T-{i}") for i in range(1, 6)]
        ts = _make_task_set(tasks)
        result = schedule_tasks(ts, start_from="T-3")
        assert [t.task_no for t in result] == ["T-3", "T-4", "T-5"]

    def test_start_from_nonexistent_returns_all(self):
        tasks = [_make_task("T-1"), _make_task("T-2")]
        ts = _make_task_set(tasks)
        result = schedule_tasks(ts, start_from="GHOST")
        assert len(result) == 2

    def test_empty_task_set(self):
        ts = _make_task_set([])
        result = schedule_tasks(ts)
        assert result == []


# ─── validate_dependencies ────────────────────────────────────────


class TestValidateDependencies:
    def test_no_dependencies_passes(self):
        ts = _make_task_set([_make_task("T-1"), _make_task("T-2")])
        result = validate_dependencies(ts)
        assert result.ok

    def test_valid_dependency_passes(self):
        tasks = [_make_task("T-1"), _make_task("T-2", depends_on="T-1")]
        ts = _make_task_set(tasks)
        result = validate_dependencies(ts)
        assert result.ok

    def test_missing_dependency_is_error(self):
        tasks = [_make_task("T-2", depends_on="T-GHOST")]
        ts = _make_task_set(tasks)
        result = validate_dependencies(ts)
        assert not result.ok
        assert any("T-GHOST" in e for e in result.errors)

    def test_direct_cycle_detected(self):
        tasks = [
            _make_task("T-1", depends_on="T-2"),
            _make_task("T-2", depends_on="T-1"),
        ]
        ts = _make_task_set(tasks)
        result = validate_dependencies(ts)
        assert not result.ok
        assert any("cycle" in e.lower() for e in result.errors)

    def test_chain_dependency_valid(self):
        tasks = [
            _make_task("T-1"),
            _make_task("T-2", depends_on="T-1"),
            _make_task("T-3", depends_on="T-2"),
        ]
        ts = _make_task_set(tasks)
        result = validate_dependencies(ts)
        assert result.ok


# ─── get_execution_plan ───────────────────────────────────────────


class TestGetExecutionPlan:
    def test_independent_tasks_in_one_wave(self):
        tasks = [_make_task("T-1"), _make_task("T-2"), _make_task("T-3")]
        ts = _make_task_set(tasks)
        waves = get_execution_plan(ts)
        assert len(waves) == 1
        assert len(waves[0]) == 3

    def test_dependent_tasks_in_separate_waves(self):
        tasks = [
            _make_task("T-1"),
            _make_task("T-2", depends_on="T-1"),
            _make_task("T-3", depends_on="T-2"),
        ]
        ts = _make_task_set(tasks)
        waves = get_execution_plan(ts)
        assert len(waves) == 3
        assert waves[0][0].task_no == "T-1"
        assert waves[1][0].task_no == "T-2"
        assert waves[2][0].task_no == "T-3"

    def test_empty_task_set_produces_no_waves(self):
        ts = _make_task_set([])
        waves = get_execution_plan(ts)
        assert waves == []

    def test_all_tasks_covered(self):
        tasks = [_make_task(f"T-{i}") for i in range(1, 6)]
        ts = _make_task_set(tasks)
        waves = get_execution_plan(ts)
        scheduled = [t for wave in waves for t in wave]
        assert len(scheduled) == 5
