"""
Task scheduler for Auto Task Runner v3.0.

Provides sorting (batch + priority), filtering, dependency validation,
and execution plan generation.
"""

from .task_set import Task, TaskSet
from .validators import ValidationResult


def schedule_tasks(
    task_set: TaskSet,
    batch: int | None = None,
    min_priority: int | None = None,
    status_filter: str | None = None,
    start_from: str | None = None,
    retry_failed: bool = False,
) -> list[Task]:
    """
    Sort and filter tasks for execution.

    Sorting: batch ASC, priority ASC, original order.
    Filtering: batch, min_priority, status, start_from, retry_failed.
    """
    tasks = list(task_set.tasks)

    # Sort by batch ASC, then priority ASC
    tasks.sort(key=lambda t: (t.batch, t.priority))

    # Filter by batch
    if batch is not None:
        tasks = [t for t in tasks if t.batch == batch]

    # Filter by min priority
    if min_priority is not None:
        tasks = [t for t in tasks if t.priority <= min_priority]

    # Filter by status
    if status_filter:
        tasks = [t for t in tasks if t.status == status_filter]

    # Retry failed / interrupted only
    if retry_failed:
        tasks = [t for t in tasks if t.status in {"failed", "interrupted"}]

    # Start from a specific task
    if start_from:
        found = False
        filtered = []
        for t in tasks:
            if t.task_no == start_from:
                found = True
            if found:
                filtered.append(t)
        if found:
            tasks = filtered
        # If not found, return all (caller should handle the error)

    return tasks


def validate_dependencies(task_set: TaskSet) -> ValidationResult:
    """
    Validate task dependencies: check for missing references and cycles.
    """
    result = ValidationResult()
    task_map = {t.task_no: t for t in task_set.tasks}

    # Check for missing dependency references
    for task in task_set.tasks:
        if task.depends_on and task.depends_on not in task_map:
            result.add_error(
                f"Task '{task.task_no}' depends on '{task.depends_on}' which doesn't exist"
            )

    # Check for cycles using DFS
    visited = set()
    in_stack = set()

    def _dfs(task_no: str) -> bool:
        """Returns True if a cycle is detected."""
        if task_no in in_stack:
            return True
        if task_no in visited:
            return False
        if task_no not in task_map:
            return False

        visited.add(task_no)
        in_stack.add(task_no)

        dep = task_map[task_no].depends_on
        if dep and _dfs(dep):
            result.add_error(f"Dependency cycle detected involving task '{task_no}'")
            return True

        in_stack.discard(task_no)
        return False

    for task in task_set.tasks:
        if task.task_no not in visited:
            _dfs(task.task_no)

    return result


def get_execution_plan(task_set: TaskSet) -> list[list[Task]]:
    """
    Group tasks into execution waves.

    Tasks in the same batch with no inter-dependencies form a wave
    that could theoretically run in parallel. Tasks with dependencies
    are placed in later waves.
    """
    tasks = list(task_set.tasks)
    tasks.sort(key=lambda t: (t.batch, t.priority))

    task_map = {t.task_no: t for t in tasks}
    completed = set()
    waves = []
    remaining = {t.task_no for t in tasks}

    max_iterations = len(tasks) + 1
    iteration = 0

    while remaining and iteration < max_iterations:
        iteration += 1
        wave = []
        for task_no in list(remaining):
            task = task_map[task_no]
            # A task is ready if it has no dependency or its dependency is completed
            if task.depends_on is None or task.depends_on in completed:
                wave.append(task)

        if not wave:
            # Remaining tasks have unresolvable dependencies
            wave = [task_map[no] for no in sorted(remaining)]
            waves.append(wave)
            break

        # Sort wave by batch, priority
        wave.sort(key=lambda t: (t.batch, t.priority))
        waves.append(wave)

        for t in wave:
            completed.add(t.task_no)
            remaining.discard(t.task_no)

    return waves
