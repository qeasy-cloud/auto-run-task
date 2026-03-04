"""
Notification system for Auto Task Runner v3.0.

Supports sending notifications on batch completion, task failure, and
interruption events via configurable webhook integrations.

Currently implemented:
  - WeCom (企业微信) — markdown_v2 format via group bot webhook

Future extensions (abstract interface ready):
  - DingTalk (钉钉)
  - Feishu / Lark (飞书)

Design principles:
  - Zero external dependencies — uses only ``urllib.request``
  - Notification failures NEVER block task execution
  - All network I/O runs with a 10-second timeout
  - Message content is truncated to stay within API limits
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import certifi
except Exception:  # pragma: no cover - optional dependency
    certifi = None

# ─── Constants ────────────────────────────────────────────────────

ENV_WECOM_WEBHOOK = "TASK_RUNNER_WECOM_WEBHOOK"
ENV_NOTIFY_ENABLED = "TASK_RUNNER_NOTIFY_ENABLED"

WECOM_MAX_CONTENT_BYTES = 4096
WECOM_SEND_TIMEOUT = 10


# ─── Abstract Base ───────────────────────────────────────────────


class Notifier(ABC):
    """Abstract notification channel.

    Subclass this to add DingTalk, Feishu, or any other webhook-based
    notification backend.
    """

    @abstractmethod
    def send_markdown(self, content: str) -> bool:
        """Send a markdown-formatted message.

        Args:
            content: Markdown text to send.

        Returns:
            True if the message was delivered successfully.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this notifier (e.g. 'WeCom')."""
        ...


# ─── WeCom (企业微信) ────────────────────────────────────────────


class WeComNotifier(Notifier):
    """企业微信群机器人 webhook 通知.

    Uses the ``markdown_v2`` message type which supports richer formatting
    (tables, code blocks, ordered lists) compared to the legacy ``markdown``
    type.  Content is capped at 4096 UTF-8 bytes per API requirement.
    """

    def __init__(self, webhook_url: str):
        if not webhook_url:
            raise ValueError("WeCom webhook URL must not be empty")
        self._webhook_url = webhook_url

    def name(self) -> str:
        return "WeCom"

    def send_markdown(self, content: str) -> bool:
        safe_content = truncate_utf8(content, WECOM_MAX_CONTENT_BYTES)
        payload = {
            "msgtype": "markdown_v2",
            "markdown_v2": {"content": safe_content},
        }
        return self._post(payload)

    def _post(self, payload: dict) -> bool:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self._webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            ssl_context = _build_ssl_context()
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                urllib.request.HTTPSHandler(context=ssl_context),
            )
            with opener.open(req, timeout=WECOM_SEND_TIMEOUT) as resp:
                body = json.loads(resp.read())
                if body.get("errcode") != 0:
                    logger.warning(
                        "WeCom API returned error: errcode=%s errmsg=%s",
                        body.get("errcode"),
                        body.get("errmsg"),
                    )
                    return False
                return True
        except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("WeCom notification failed: %s", exc)
            return False


# ─── Notifier Factory ────────────────────────────────────────────


def create_notifier(
    webhook_url: str | None = None,
    enabled: bool | None = None,
) -> Notifier | None:
    """Create a notifier from explicit args or environment variables.

    Resolution order for webhook URL:
      1. Explicit ``webhook_url`` argument
      2. ``TASK_RUNNER_WECOM_WEBHOOK`` environment variable

    The notifier is disabled (returns None) when:
      - ``enabled`` is explicitly False
      - ``TASK_RUNNER_NOTIFY_ENABLED`` is ``"false"`` / ``"0"``
      - No webhook URL is available
    """
    if enabled is False:
        return None

    env_enabled = os.environ.get(ENV_NOTIFY_ENABLED, "").strip().lower()
    if env_enabled in ("false", "0", "no", "off"):
        return None

    url = webhook_url or os.environ.get(ENV_WECOM_WEBHOOK, "").strip()
    if not url:
        return None

    return WeComNotifier(url)


# ─── Message Builders ────────────────────────────────────────────


def build_batch_complete_message(
    *,
    project: str,
    task_set: str,
    start_time: str,
    end_time: str,
    duration: str,
    succeeded: int,
    failed: int,
    skipped: int,
    total: int,
    total_done: int,
    interrupted: bool,
    failed_tasks: list[dict] | None = None,
) -> str:
    """Build a markdown_v2 message for batch / full completion."""
    if interrupted:
        title = "🤖 轻易云自动机器人｜执行中断"
    elif failed > 0:
        title = "🤖 轻易云自动机器人｜执行完成（有失败）"
    else:
        title = "🤖 轻易云自动机器人｜全部完成"

    lines: list[str] = []
    lines.append(f"## {title}")
    lines.append("")
    overall_status = "⚠️ 已中断" if interrupted else ("❌ 存在失败" if failed > 0 else "✅ 全部成功")
    lines.append(f"**总体状态:** {overall_status}")
    lines.append(f"**项目:** {project}")
    lines.append(f"**任务集:** {task_set}")
    lines.append(f"**执行时间:** {start_time} ~ {end_time} ({duration})")
    lines.append("")

    lines.append("### 执行结果")
    lines.append("")
    lines.append("| 状态 | 数量 |")
    lines.append("| :--- | ---: |")
    lines.append(f"| 成功 | {succeeded} |")
    lines.append(f"| 失败 | {failed} |")
    lines.append(f"| 跳过 | {skipped} |")
    lines.append(f"| 总进度 | {total_done}/{total} |")

    if failed_tasks:
        lines.append("")
        lines.append("### 失败任务")
        lines.append("")
        for ft in failed_tasks:
            task_no = ft.get("task_no", "?")
            reason = ft.get("failure_reason", "exit code != 0")
            dur = ft.get("duration_seconds", 0)
            dur_str = _format_duration(dur)
            lines.append(f"- **{task_no}** — {reason} ({dur_str})")

    if interrupted:
        lines.append("")
        lines.append("> 执行被用户中断 (Ctrl+C)")

    return "\n".join(lines)


def build_task_failure_message(
    *,
    project: str,
    task_set: str,
    task_no: str,
    task_name: str,
    failure_reason: str,
    elapsed: str,
    tool: str | None = None,
    model: str | None = None,
    return_code: int | None = None,
    output_tail: str | None = None,
    log_file: str | None = None,
) -> str:
    """Build a markdown_v2 message for a single task failure."""
    lines: list[str] = []
    lines.append("## 🤖 轻易云自动机器人｜任务失败")
    lines.append("")
    lines.append("**状态:** ❌ 失败")
    lines.append(f"**项目:** {project} / {task_set}")
    lines.append(f"**任务:** {task_no} {task_name}")
    if tool:
        lines.append(f"**执行工具:** {tool}")
    if model:
        lines.append(f"**模型:** {model}")
    if return_code is not None:
        lines.append(f"**退出码:** {return_code}")
    lines.append(f"**失败原因:** {failure_reason}")
    lines.append(f"**耗时:** {elapsed}")
    suffix_lines = [""]
    compact_output = _fit_output_by_budget(lines, output_tail, suffix_lines)
    if compact_output:
        lines.append("")
        lines.append("### 最终结果输出")
        lines.append(compact_output)

    lines.extend(suffix_lines)
    return "\n".join(lines)


def build_interrupt_message(
    *,
    project: str,
    task_set: str,
    current_task_no: str,
    current_task_name: str,
    completed: int,
    total: int,
) -> str:
    """Build a markdown_v2 message for execution interruption (Ctrl+C)."""
    now_str = datetime.now().strftime("%H:%M:%S")
    lines: list[str] = []
    lines.append("## 🤖 轻易云自动机器人｜执行中断")
    lines.append("")
    lines.append("**状态:** ⚠️ 中断")
    lines.append(f"**项目:** {project} / {task_set}")
    lines.append(f"**中断时间:** {now_str}")
    lines.append(f"**当前任务:** {current_task_no} {current_task_name}")
    lines.append(f"**已完成:** {completed}/{total}")
    return "\n".join(lines)


def build_task_complete_message(
    *,
    project: str,
    task_set: str,
    task_no: str,
    task_name: str,
    elapsed: str,
    tool: str | None = None,
    model: str | None = None,
    return_code: int | None = None,
    progress_done: int | None = None,
    progress_total: int | None = None,
    output_tail: str | None = None,
    log_file: str | None = None,
    next_task_no: str | None = None,
    next_task_name: str | None = None,
    next_tool: str | None = None,
    next_model: str | None = None,
) -> str:
    """Build a markdown_v2 message for a single task success (opt-in via --notify-each)."""
    lines: list[str] = []
    lines.append("## 🤖 轻易云自动机器人｜任务完成")
    lines.append("")
    lines.append("**状态:** ✅ 成功")
    lines.append(f"**项目:** {project} / {task_set}")
    lines.append(f"**任务:** {task_no} {task_name}")
    if tool:
        lines.append(f"**执行工具:** {tool}")
    if model:
        lines.append(f"**模型:** {model}")
    if return_code is not None:
        lines.append(f"**退出码:** {return_code}")
    lines.append(f"**耗时:** {elapsed}")
    if progress_done is not None and progress_total:
        pct = (progress_done / progress_total) * 100
        lines.append(f"**当前进度:** {progress_done}/{progress_total} ({pct:.1f}%)")
    suffix_lines: list[str] = [""]
    if next_task_no:
        next_title = f"{next_task_no} {next_task_name}" if next_task_name else str(next_task_no)
        suffix_lines.append("### 下一任务预告")
        suffix_lines.append(f"- {next_title}")
        if next_tool:
            suffix_lines.append(f"- 工具: {next_tool}")
        if next_model:
            suffix_lines.append(f"- 模型: {next_model}")
    else:
        suffix_lines.append("### 下一任务预告")
        suffix_lines.append("- 当前任务集已无待执行任务")

    compact_output = _fit_output_by_budget(lines, output_tail, suffix_lines)
    if compact_output:
        lines.append("")
        lines.append("### 最终结果输出")
        lines.append(compact_output)

    lines.extend(suffix_lines)
    return "\n".join(lines)


# ─── Helpers ─────────────────────────────────────────────────────


def truncate_utf8(text: str, max_bytes: int) -> str:
    """Truncate *text* so its UTF-8 encoding is at most *max_bytes* bytes.

    If truncation is necessary, a trailing ``\\n\\n> (内容已截断)`` note is
    appended, and the main body is shortened to make room.
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text

    suffix = "\n\n> (内容已截断)"
    suffix_bytes = len(suffix.encode("utf-8"))
    target = max_bytes - suffix_bytes

    if target <= 0:
        return suffix.strip()

    # Truncate at a valid UTF-8 char boundary
    truncated = encoded[:target].decode("utf-8", errors="ignore")
    return truncated + suffix


def _format_duration(seconds: float) -> str:
    total_secs = int(seconds)
    hours, remainder = divmod(total_secs, 3600)
    mins, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {mins:02d}m {secs:02d}s"
    elif mins > 0:
        return f"{mins}m {secs:02d}s"
    else:
        return f"{secs}s"


def _compact_result_text(text: str | None, *, max_lines: int = 10, max_chars: int = 700) -> str:
    if not text:
        return ""
    normalized = text.strip()
    if not normalized:
        return ""
    lines = normalized.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    compact = "\n".join(lines)
    if len(compact) > max_chars:
        compact = compact[-max_chars:]
        compact = f"...(截断)\n{compact}"
    return compact


def _fit_output_by_budget(
    prefix_lines: list[str],
    output_tail: str | None,
    suffix_lines: list[str],
    *,
    target_bytes: int = WECOM_MAX_CONTENT_BYTES,
) -> str:
    """Fit output snippet within byte budget while keeping key fields visible.

    Strategy:
      1) Reserve space for prefix + suffix + wrapper markdown.
      2) Iteratively shrink output (lines/chars/bytes) until total fits.
      3) Fall back to empty output when budget is insufficient.
    """
    if not output_tail or not output_tail.strip():
        return ""

    wrapper = ["\n### 最终结果输出", ""]
    base_bytes = len("\n".join(prefix_lines + wrapper + suffix_lines).encode("utf-8"))
    available = target_bytes - base_bytes - 96
    if available <= 80:
        return ""

    max_lines = 18
    max_chars = min(2200, max(300, available * 2))

    for _ in range(8):
        compact = _compact_result_text(output_tail, max_lines=max_lines, max_chars=max_chars)
        compact_bytes = len(compact.encode("utf-8"))
        if compact_bytes <= available:
            return compact
        max_lines = max(3, max_lines - 2)
        max_chars = max(120, int(max_chars * 0.7))

    return _compact_result_text(output_tail, max_lines=3, max_chars=120)


def _build_ssl_context() -> ssl.SSLContext:
    """Build SSL context for webhook calls.

    Preference order:
      1) certifi CA bundle (if installed)
      2) system default trust store
    """
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def send_notification_safe(notifier: Notifier | None, content: str) -> None:
    """Fire-and-forget: send a notification, swallowing all exceptions.

    This is the entry-point that the executor should call — it guarantees
    that notification failures never propagate into the task execution flow.
    """
    if notifier is None:
        return
    try:
        ok = notifier.send_markdown(content)
        if ok:
            logger.info("Notification sent via %s", notifier.name())
        else:
            logger.warning("Notification via %s returned failure", notifier.name())
    except Exception as exc:
        logger.warning("Notification via %s raised exception: %s", notifier.name(), exc)
