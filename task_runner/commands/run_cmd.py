"""
Run command: orchestrate the full execution flow.

Supports executing one or more task sets sequentially within a project.
"""

import signal
import time
from datetime import datetime

from ..config import get_tool_config
from ..display import (
    show_error,
    show_info,
    show_multi_task_set_header,
    show_multi_task_set_summary,
    show_task_set_divider,
)
from ..project import (
    RunRecord,
    add_run_record,
    get_project_dir,
    load_project,
    save_project,
    update_project_status,
)
from ..runtime import (
    backup_task_set,
    create_run_context,
    save_run_metadata,
    save_run_summary,
    update_latest_symlink,
)
from ..scheduler import schedule_tasks
from ..task_set import discover_task_sets, load_task_set


def handle_run(args) -> int:
    """Execute tasks in a project (one or more task sets)."""
    return _dispatch(args, dry_run=False)


def _resolve_task_set_names(args, project_name: str) -> list[str] | None:
    """Resolve the list of task set names from CLI args.

    Returns a list of task set names, or None on error.
    """
    run_all = getattr(args, "run_all", False)
    names = getattr(args, "task_set_names", []) or []

    if not names and not run_all:
        show_error(
            "Please specify task set name(s) or use --all.\n"
            "  Example: python run.py run PROJECT task1 task2\n"
            "  Example: python run.py run PROJECT --all"
        )
        return None

    if run_all:
        # Load project to check task_set_order
        try:
            config = load_project(project_name)
        except FileNotFoundError:
            show_error(f"Project '{project_name}' not found!")
            return None

        project_dir = get_project_dir(project_name)
        all_sets = discover_task_sets(project_dir)

        if not all_sets:
            show_error(f"No task sets found in project '{project_name}'!")
            return None

        # Use task_set_order if defined, otherwise alphabetical
        if config.task_set_order:
            ordered = []
            for name in config.task_set_order:
                if name in all_sets:
                    ordered.append(name)
                else:
                    show_error(
                        f"Task set '{name}' in task_set_order not found in project '{project_name}'!"
                    )
                    return None
            # Append any discovered sets not listed in order
            for name in all_sets:
                if name not in ordered:
                    ordered.append(name)
            return ordered

        return all_sets

    # Validate specified names exist
    project_dir = get_project_dir(project_name)
    all_sets = discover_task_sets(project_dir)
    for name in names:
        if name not in all_sets:
            show_error(
                f"Task set '{name}' not found in project '{project_name}'!\n"
                f"  Available: {', '.join(all_sets)}"
            )
            return None

    return names


def _dispatch(args, dry_run: bool = False) -> int:
    """Resolve task sets and dispatch to single or multi execution."""
    project_name = args.project_name
    task_set_names = _resolve_task_set_names(args, project_name)
    if task_set_names is None:
        return 1

    if len(task_set_names) == 1:
        return _execute_single(args, task_set_names[0], dry_run=dry_run)

    return _execute_multi(args, task_set_names, dry_run=dry_run)


def _execute_multi(args, task_set_names: list[str], dry_run: bool = False) -> int:
    """Execute multiple task sets sequentially."""
    project_name = args.project_name
    stop_on_error = getattr(args, "stop_on_error", False)

    # ── Daemon mode detection (must run before any display calls) ──
    import sys as _sys

    from ..display import auto_detect_daemon_mode, enable_daemon_mode

    daemon = getattr(args, "daemon", False)
    if daemon:
        enable_daemon_mode()
    elif not _sys.stdout.isatty():
        auto_detect_daemon_mode()

    # Show multi-task-set header
    show_multi_task_set_header(task_set_names, project_name)

    results: list[dict] = []
    overall_start = time.time()
    interrupted = False

    for idx, ts_name in enumerate(task_set_names):
        show_task_set_divider(idx + 1, len(task_set_names), ts_name)

        ts_start = time.time()
        interrupt_flag: list[bool] = []

        try:
            code = _execute_single(
                args, ts_name, dry_run=dry_run, _interrupt_flag=interrupt_flag
            )
        except KeyboardInterrupt:
            interrupted = True
            code = 130
            results.append({
                "task_set_name": ts_name,
                "code": code,
                "elapsed": time.time() - ts_start,
            })
            break

        ts_elapsed = time.time() - ts_start
        results.append({
            "task_set_name": ts_name,
            "code": code,
            "elapsed": ts_elapsed,
        })

        # Restore default signal handling between task sets so CTRL+C
        # raises KeyboardInterrupt and SIGTERM terminates cleanly
        # (executor installs its own handlers for both signals)
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

        # Stop if interrupted inside executor
        if interrupt_flag:
            interrupted = True
            break

        # Stop on error if requested
        if stop_on_error and code != 0:
            show_info(f"Stopping: task set '{ts_name}' failed (--stop-on-error)")
            break

    overall_elapsed = time.time() - overall_start
    show_multi_task_set_summary(results, overall_elapsed, interrupted=interrupted)

    return 0 if all(r["code"] == 0 for r in results) else 1


def _execute_single(
    args,
    task_set_name: str,
    dry_run: bool = False,
    _interrupt_flag: list[bool] | None = None,
) -> int:
    """Execute a single task set. Core execution logic."""
    project_name = args.project_name

    # ── Load project ──
    try:
        config = load_project(project_name)
    except FileNotFoundError:
        show_error(f"Project '{project_name}' not found!")
        return 1

    project_dir = get_project_dir(project_name)

    # ── Resolve tool/model ──
    cli_tool = getattr(args, "tool", None)
    cli_model = getattr(args, "model", None)
    tool_name = cli_tool or config.default_tool
    model = cli_model or config.default_model

    try:
        tool_config = get_tool_config(tool_name)
    except KeyError as e:
        show_error(str(e))
        return 1

    # Model validation
    if (
        model
        and tool_config.supports_model
        and tool_config.models
        and model not in tool_config.models
    ):
        show_error(
            f"Unknown model '{model}' for tool '{tool_name}'. "
            f"Available: {', '.join(tool_config.models)}"
        )
        return 1
    if not tool_config.supports_model:
        model = None
    elif not model and tool_config.default_model:
        model = tool_config.default_model

    # ── Load task set ──
    try:
        task_set = load_task_set(
            project_dir,
            task_set_name,
            project_defaults={
                "default_tool": config.default_tool,
                "default_model": config.default_model,
            },
        )
    except FileNotFoundError:
        show_error(f"Task set '{task_set_name}' not found in project '{project_name}'!")
        return 1

    # ── Schedule tasks ──
    batch_filter = getattr(args, "batch", None)
    min_priority = getattr(args, "min_priority", None)
    start_from = getattr(args, "start", None)
    retry_failed = getattr(args, "retry_failed", False)

    scheduled = schedule_tasks(
        task_set,
        batch=batch_filter,
        min_priority=min_priority,
        start_from=start_from,
        retry_failed=retry_failed,
    )

    if not scheduled:
        show_info(f"No tasks to execute in '{task_set_name}' after filtering.")
        return 0

    # ── Resolve proxy ──
    proxy_mode = getattr(args, "proxy_mode", None)
    if proxy_mode == "on":
        use_proxy = True
    elif proxy_mode == "off":
        use_proxy = False
    else:
        use_proxy = tool_config.needs_proxy

    # ── Resolve template ──
    template_override = getattr(args, "template", None)

    # ── Resolve work dir ──
    work_dir_override = getattr(args, "work_dir", None)
    workspace = work_dir_override or config.workspace

    # ── Heartbeat ──
    heartbeat = getattr(args, "heartbeat", 60)

    # ── Output control ──
    verbose = getattr(args, "verbose", False)
    quiet = getattr(args, "quiet", False)
    no_color = getattr(args, "no_color", False)
    daemon = getattr(args, "daemon", False)

    # ── Daemon / supervisor mode ──
    import sys as _sys

    from ..display import auto_detect_daemon_mode, enable_daemon_mode, is_daemon_mode

    if daemon:
        enable_daemon_mode()
    elif not _sys.stdout.isatty():
        auto_detect_daemon_mode()

    if is_daemon_mode():
        no_color = True

    if no_color:
        from ..display import console as _console

        _console.no_color = True

    if verbose:
        heartbeat = min(heartbeat, 15)

    # ── Create run context ──
    filters = {
        "batch": batch_filter,
        "min_priority": min_priority,
        "start_from": start_from,
        "retry_failed": retry_failed,
    }

    run_ctx = create_run_context(
        project_dir=project_dir,
        task_set_name=task_set_name,
        tool=tool_name,
        model=model,
        workspace=workspace,
        filters=filters,
        total_tasks=len(task_set.tasks),
        tasks_to_execute=len(scheduled),
    )

    # ── Backup task set ──
    backup_task_set(project_dir, task_set_name)

    # ── Save run metadata ──
    save_run_metadata(run_ctx)

    # ── Add run record ──
    run_record = RunRecord(
        run_at=run_ctx.run_id,
        status="running",
        task_set_name=task_set_name,
    )
    add_run_record(config, run_record)

    # ── Update project status ──
    if config.status == "planned":
        update_project_status(config, "active")

    # ── Git safety ──
    git_safety = getattr(args, "git_safety", False)

    # ── Create executor and run ──
    from ..executor import TaskExecutor, parse_delay_range

    delay_range = parse_delay_range(getattr(args, "delay", None))

    from ..config import MAX_EXECUTION_SECONDS

    cli_timeout = getattr(args, "timeout", None)
    max_execution_seconds = cli_timeout if cli_timeout is not None else MAX_EXECUTION_SECONDS

    # ── Notification settings ──
    notify_enabled = getattr(args, "notify_enabled", None)
    notify_each = getattr(args, "notify_each", False)
    wecom_webhook = getattr(args, "wecom_webhook", None)

    executor = TaskExecutor(
        project_config=config,
        task_set=task_set,
        scheduled_tasks=scheduled,
        run_context=run_ctx,
        tool_config=tool_config,
        model=model,
        use_proxy=use_proxy,
        proxy_mode=proxy_mode,
        cli_tool_override=cli_tool is not None,
        cli_model_override=cli_model is not None,
        dry_run=dry_run,
        heartbeat_interval=heartbeat,
        workspace=workspace,
        template_override=template_override,
        git_safety=git_safety,
        verbose=verbose,
        quiet=quiet,
        delay_range=delay_range,
        max_execution_seconds=max_execution_seconds,
        notify_enabled=notify_enabled,
        notify_each=notify_each,
        wecom_webhook=wecom_webhook,
    )

    result_code = executor.run()

    # Propagate interrupt flag to caller
    if _interrupt_flag is not None and executor.interrupted:
        _interrupt_flag.append(True)

    # ── Save run summary ──
    results = executor.get_results()
    task_results = executor.get_task_results()
    save_run_summary(run_ctx, results, task_results)

    # ── Update run record ──
    now = datetime.now()
    run_record.stop_at = now.strftime("%Y-%m-%d_%H-%M-%S")
    started = datetime.strptime(run_record.run_at, "%Y-%m-%d_%H-%M-%S")
    run_record.cumulated_minutes = round((now - started).total_seconds() / 60, 1)
    run_record.status = "completed" if results.get("failed", 0) == 0 else "partial"
    run_record.tasks_attempted = results.get("attempted", 0)
    run_record.tasks_succeeded = results.get("succeeded", 0)
    run_record.tasks_failed = results.get("failed", 0)
    save_project(config)

    # ── Update latest symlink ──
    update_latest_symlink(project_dir, run_ctx.run_dir)

    return result_code
