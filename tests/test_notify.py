"""Tests for task_runner.notify module."""

import json
import os
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from task_runner.notify import (
    ENV_NOTIFY_ENABLED,
    ENV_WECOM_WEBHOOK,
    WECOM_MAX_CONTENT_BYTES,
    Notifier,
    WeComNotifier,
    build_batch_complete_message,
    build_interrupt_message,
    build_task_complete_message,
    build_task_failure_message,
    create_notifier,
    send_notification_safe,
    truncate_utf8,
)

FAKE_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key"


# ─── Helper ──────────────────────────────────────────────────────


def _make_urlopen_response(body: dict, status: int = 200) -> MagicMock:
    """Build a mock that behaves like ``urllib.request.urlopen()`` return value."""
    data = json.dumps(body).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = data
    resp.status = status
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ─── truncate_utf8 ───────────────────────────────────────────────


class TestTruncateUtf8:
    def test_no_truncation_needed(self):
        text = "hello world"
        assert truncate_utf8(text, 100) == text

    def test_exact_boundary(self):
        text = "abc"
        assert truncate_utf8(text, 3) == text

    def test_truncates_long_text(self):
        text = "a" * 5000
        result = truncate_utf8(text, 4096)
        assert len(result.encode("utf-8")) <= 4096
        assert result.endswith("(内容已截断)")

    def test_preserves_utf8_char_boundary(self):
        text = "中" * 2000  # each '中' is 3 bytes → 6000 bytes total
        result = truncate_utf8(text, 4096)
        encoded = result.encode("utf-8")
        assert len(encoded) <= 4096
        # Should not produce invalid UTF-8
        encoded.decode("utf-8")

    def test_very_small_limit(self):
        text = "hello world"
        result = truncate_utf8(text, 10)
        # When limit is too small for body + suffix, we get just the stripped suffix
        suffix_full = "\n\n> (内容已截断)"
        assert len(result.encode("utf-8")) <= max(10, len(suffix_full.encode("utf-8")))

    def test_empty_text(self):
        assert truncate_utf8("", 100) == ""

    def test_mixed_ascii_and_unicode(self):
        text = "Status: 成功 " * 500
        result = truncate_utf8(text, 4096)
        assert len(result.encode("utf-8")) <= 4096


# ─── WeComNotifier ───────────────────────────────────────────────


class TestWeComNotifier:
    def test_init_empty_url_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            WeComNotifier("")

    def test_name(self):
        n = WeComNotifier(FAKE_WEBHOOK)
        assert n.name() == "WeCom"

    @patch("task_runner.notify.urllib.request.urlopen")
    def test_send_markdown_success(self, mock_urlopen):
        mock_urlopen.return_value = _make_urlopen_response({"errcode": 0, "errmsg": "ok"})
        n = WeComNotifier(FAKE_WEBHOOK)
        assert n.send_markdown("## test") is True

        # Verify the request was built correctly
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.get_method() == "POST"
        assert req.get_header("Content-type") == "application/json"

        payload = json.loads(req.data.decode("utf-8"))
        assert payload["msgtype"] == "markdown_v2"
        assert payload["markdown_v2"]["content"] == "## test"

    @patch("task_runner.notify.urllib.request.urlopen")
    def test_send_markdown_api_error(self, mock_urlopen):
        mock_urlopen.return_value = _make_urlopen_response(
            {"errcode": 93000, "errmsg": "invalid webhook url"}
        )
        n = WeComNotifier(FAKE_WEBHOOK)
        assert n.send_markdown("test") is False

    @patch("task_runner.notify.urllib.request.urlopen")
    def test_send_markdown_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        n = WeComNotifier(FAKE_WEBHOOK)
        assert n.send_markdown("test") is False

    @patch("task_runner.notify.urllib.request.urlopen")
    def test_send_markdown_truncates_long_content(self, mock_urlopen):
        mock_urlopen.return_value = _make_urlopen_response({"errcode": 0, "errmsg": "ok"})
        n = WeComNotifier(FAKE_WEBHOOK)
        long_content = "x" * 10000
        n.send_markdown(long_content)

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        content = payload["markdown_v2"]["content"]
        assert len(content.encode("utf-8")) <= WECOM_MAX_CONTENT_BYTES

    @patch("task_runner.notify.urllib.request.urlopen")
    def test_send_markdown_json_decode_error(self, mock_urlopen):
        resp = MagicMock()
        resp.read.return_value = b"not json"
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp
        n = WeComNotifier(FAKE_WEBHOOK)
        assert n.send_markdown("test") is False


# ─── create_notifier ─────────────────────────────────────────────


class TestCreateNotifier:
    def test_explicit_url(self):
        n = create_notifier(webhook_url=FAKE_WEBHOOK)
        assert isinstance(n, WeComNotifier)

    def test_env_url(self):
        with patch.dict(os.environ, {ENV_WECOM_WEBHOOK: FAKE_WEBHOOK}):
            n = create_notifier()
            assert isinstance(n, WeComNotifier)

    def test_no_url_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            n = create_notifier()
            assert n is None

    def test_explicit_disabled(self):
        n = create_notifier(webhook_url=FAKE_WEBHOOK, enabled=False)
        assert n is None

    def test_env_disabled_false(self):
        with patch.dict(os.environ, {ENV_WECOM_WEBHOOK: FAKE_WEBHOOK, ENV_NOTIFY_ENABLED: "false"}):
            n = create_notifier()
            assert n is None

    def test_env_disabled_zero(self):
        with patch.dict(os.environ, {ENV_WECOM_WEBHOOK: FAKE_WEBHOOK, ENV_NOTIFY_ENABLED: "0"}):
            n = create_notifier()
            assert n is None

    def test_env_disabled_off(self):
        with patch.dict(os.environ, {ENV_WECOM_WEBHOOK: FAKE_WEBHOOK, ENV_NOTIFY_ENABLED: "off"}):
            n = create_notifier()
            assert n is None

    def test_env_enabled_true(self):
        with patch.dict(os.environ, {ENV_WECOM_WEBHOOK: FAKE_WEBHOOK, ENV_NOTIFY_ENABLED: "true"}):
            n = create_notifier()
            assert isinstance(n, WeComNotifier)

    def test_explicit_url_overrides_env(self):
        other_url = "https://example.com/other"
        with patch.dict(os.environ, {ENV_WECOM_WEBHOOK: FAKE_WEBHOOK}):
            n = create_notifier(webhook_url=other_url)
            assert isinstance(n, WeComNotifier)
            assert n._webhook_url == other_url


# ─── send_notification_safe ──────────────────────────────────────


class TestSendNotificationSafe:
    def test_none_notifier(self):
        # Should not raise
        send_notification_safe(None, "test")

    def test_success(self):
        mock = MagicMock(spec=Notifier)
        mock.send_markdown.return_value = True
        mock.name.return_value = "TestBot"
        send_notification_safe(mock, "hello")
        mock.send_markdown.assert_called_once_with("hello")

    def test_failure_does_not_raise(self):
        mock = MagicMock(spec=Notifier)
        mock.send_markdown.return_value = False
        mock.name.return_value = "TestBot"
        send_notification_safe(mock, "hello")

    def test_exception_does_not_raise(self):
        mock = MagicMock(spec=Notifier)
        mock.send_markdown.side_effect = RuntimeError("boom")
        mock.name.return_value = "TestBot"
        # Must NOT propagate exception
        send_notification_safe(mock, "hello")


# ─── Message Builders ───────────────────────────────────────────


class TestBuildBatchCompleteMessage:
    def test_all_success(self):
        msg = build_batch_complete_message(
            project="MY_PROJECT",
            task_set="my-tasks",
            start_time="14:30:05",
            end_time="16:45:30",
            duration="2h 15m 25s",
            succeeded=12,
            failed=0,
            skipped=1,
            total=15,
            total_done=13,
            interrupted=False,
        )
        assert "全部完成" in msg
        assert "MY_PROJECT" in msg
        assert "my-tasks" in msg
        assert "14:30:05" in msg
        assert "16:45:30" in msg
        assert "12" in msg

    def test_with_failures(self):
        msg = build_batch_complete_message(
            project="P",
            task_set="ts",
            start_time="10:00:00",
            end_time="11:00:00",
            duration="1h 00m 00s",
            succeeded=8,
            failed=2,
            skipped=0,
            total=10,
            total_done=8,
            interrupted=False,
            failed_tasks=[
                {"task_no": "M18", "failure_reason": "timeout", "duration_seconds": 2400},
                {"task_no": "M22", "failure_reason": "exit code 1", "duration_seconds": 120},
            ],
        )
        assert "有失败" in msg
        assert "M18" in msg
        assert "timeout" in msg
        assert "M22" in msg

    def test_interrupted(self):
        msg = build_batch_complete_message(
            project="P",
            task_set="ts",
            start_time="10:00:00",
            end_time="10:30:00",
            duration="30m 00s",
            succeeded=5,
            failed=0,
            skipped=0,
            total=10,
            total_done=5,
            interrupted=True,
        )
        assert "中断" in msg
        assert "Ctrl+C" in msg

    def test_fits_in_4096_bytes(self):
        many_failures = [
            {"task_no": f"T-{i}", "failure_reason": "timeout", "duration_seconds": 2400}
            for i in range(200)
        ]
        msg = build_batch_complete_message(
            project="P",
            task_set="ts",
            start_time="10:00:00",
            end_time="11:00:00",
            duration="1h",
            succeeded=0,
            failed=200,
            skipped=0,
            total=200,
            total_done=0,
            interrupted=False,
            failed_tasks=many_failures,
        )
        # The message builder itself doesn't truncate — that's WeComNotifier's job.
        # But it should still produce valid markdown.
        assert "失败任务" in msg


class TestBuildTaskFailureMessage:
    def test_basic(self):
        msg = build_task_failure_message(
            project="P",
            task_set="ts",
            task_no="M18",
            task_name="物料建模",
            failure_reason="timeout",
            elapsed="40m 00s",
        )
        assert "任务失败" in msg
        assert "M18" in msg
        assert "物料建模" in msg
        assert "timeout" in msg
        assert "40m 00s" in msg


class TestBuildInterruptMessage:
    def test_basic(self):
        msg = build_interrupt_message(
            project="P",
            task_set="ts",
            current_task_no="M18",
            current_task_name="物料建模",
            completed=5,
            total=10,
        )
        assert "中断" in msg
        assert "M18" in msg
        assert "5/10" in msg


class TestBuildTaskCompleteMessage:
    def test_basic(self):
        msg = build_task_complete_message(
            project="P",
            task_set="ts",
            task_no="M10",
            task_name="会计要素建模",
            elapsed="4m 18s",
        )
        assert "任务完成" in msg
        assert "M10" in msg
        assert "4m 18s" in msg


# ─── Integration test with real webhook ──────────────────────────


class TestWeComIntegration:
    """Integration test using the real webhook.

    Only runs when TASK_RUNNER_WECOM_WEBHOOK is set.
    Sends a real test message to the configured WeCom group.
    """

    @pytest.fixture
    def webhook_url(self):
        url = os.environ.get(ENV_WECOM_WEBHOOK, "").strip()
        if not url:
            pytest.skip("TASK_RUNNER_WECOM_WEBHOOK not set")
        return url

    def test_real_send_markdown_v2(self, webhook_url):
        """Send a real test notification to verify the webhook works."""
        n = WeComNotifier(webhook_url)
        content = build_batch_complete_message(
            project="AUTO_TEST",
            task_set="unit-test",
            start_time="10:00:00",
            end_time="10:05:00",
            duration="5m 00s",
            succeeded=3,
            failed=1,
            skipped=1,
            total=5,
            total_done=3,
            interrupted=False,
            failed_tasks=[
                {"task_no": "T-2", "failure_reason": "exit code 1", "duration_seconds": 65},
            ],
        )
        result = n.send_markdown(content)
        assert result is True, "Real WeCom webhook send failed"

    def test_real_send_truncated(self, webhook_url):
        """Verify truncation works with the real API."""
        n = WeComNotifier(webhook_url)
        # Build a message that exceeds 4096 bytes
        lines = ["## Truncation Test\n"]
        lines.append("| No | Task | Status |")
        lines.append("| :--- | :--- | :--- |")
        for i in range(300):
            lines.append(f"| T-{i:03d} | 测试任务名称很长很长 {i} | 成功 |")
        content = "\n".join(lines)
        assert len(content.encode("utf-8")) > WECOM_MAX_CONTENT_BYTES
        result = n.send_markdown(content)
        assert result is True, "Truncated message send failed"


# ─── Notifier abstract interface ─────────────────────────────────


class TestNotifierInterface:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Notifier()  # type: ignore[abstract]

    def test_concrete_subclass(self):
        class DummyNotifier(Notifier):
            def send_markdown(self, content: str) -> bool:
                return True

            def name(self) -> str:
                return "Dummy"

        n = DummyNotifier()
        assert n.send_markdown("test") is True
        assert n.name() == "Dummy"
