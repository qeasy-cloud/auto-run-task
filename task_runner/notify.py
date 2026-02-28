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
    certifi = None  # type: ignore[assignment]

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
        title = "Task Runner - 执行中断"
    elif failed > 0:
        title = "Task Runner - 执行完成 (有失败)"
    else:
        title = "Task Runner - 全部完成"

    lines: list[str] = []
    lines.append(f"## {title}")
    lines.append("")
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
) -> str:
    """Build a markdown_v2 message for a single task failure."""
    lines: list[str] = []
    lines.append("## Task Runner - 任务失败")
    lines.append("")
    lines.append(f"**项目:** {project} / {task_set}")
    lines.append(f"**任务:** {task_no} {task_name}")
    lines.append(f"**失败原因:** {failure_reason}")
    lines.append(f"**耗时:** {elapsed}")
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
    lines.append("## Task Runner - 执行中断")
    lines.append("")
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
) -> str:
    """Build a markdown_v2 message for a single task success (opt-in via --notify-each)."""
    lines: list[str] = []
    lines.append("## Task Runner - 任务完成")
    lines.append("")
    lines.append(f"**项目:** {project} / {task_set}")
    lines.append(f"**任务:** {task_no} {task_name}")
    lines.append(f"**耗时:** {elapsed}")
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
