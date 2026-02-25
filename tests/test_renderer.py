"""Tests for task_runner.renderer module."""

import json

from task_runner.renderer import render_prompt

SIMPLE_TASK = {
    "task_no": "T-1",
    "task_name": "Fix login bug",
    "description": "Fix the authentication issue",
    "priority": 10,
    "status": "not-started",
}


class TestRenderPromptKeyPlaceholders:
    def test_single_key_replaced(self):
        template = "Task: {{task_name}}"
        result = render_prompt(template, SIMPLE_TASK)
        assert result == "Task: Fix login bug"

    def test_multiple_keys_replaced(self):
        template = "{{task_no}}: {{task_name}}"
        result = render_prompt(template, SIMPLE_TASK)
        assert result == "T-1: Fix login bug"

    def test_missing_key_replaced_with_empty_string(self):
        template = "{{nonexistent}}"
        result = render_prompt(template, SIMPLE_TASK)
        assert result == ""

    def test_integer_value_converted_to_string(self):
        template = "Priority: {{priority}}"
        result = render_prompt(template, SIMPLE_TASK)
        assert result == "Priority: 10"

    def test_dict_value_serialized_as_json(self):
        task = {**SIMPLE_TASK, "cli": {"tool": "copilot", "model": "claude-opus-4.6"}}
        template = "CLI: {{cli}}"
        result = render_prompt(template, task)
        parsed = json.loads(result.replace("CLI: ", ""))
        assert parsed["tool"] == "copilot"

    def test_list_value_serialized_as_json(self):
        task = {**SIMPLE_TASK, "tags": ["bug", "auth"]}
        template = "Tags: {{tags}}"
        result = render_prompt(template, task)
        parsed = json.loads(result.replace("Tags: ", ""))
        assert parsed == ["bug", "auth"]

    def test_key_with_whitespace_NOT_stripped(self):
        """The regex uses \\w+ so spaces inside {{ }} prevent matching — no substitution."""
        template = "{{ task_name }}"
        result = render_prompt(template, SIMPLE_TASK)
        # Spaces inside braces prevent regex match; placeholder is left as-is
        assert result == "{{ task_name }}"


class TestRenderPromptItemPlaceholder:
    def test_item_replaced_with_full_json(self):
        template = "#item"
        result = render_prompt(template, SIMPLE_TASK)
        data = json.loads(result)
        assert data["task_no"] == "T-1"
        assert data["task_name"] == "Fix login bug"

    def test_item_strips_cli_field(self):
        """'cli' config must be excluded from #item — it can confuse AI models."""
        task = {**SIMPLE_TASK, "cli": {"tool": "copilot", "model": "claude-opus-4.6"}}
        result = render_prompt("#item", task)
        data = json.loads(result)
        assert "cli" not in data
        # Other fields must still be present
        assert data["task_no"] == "T-1"

    def test_item_without_cli_field_unaffected(self):
        """Tasks without 'cli' should serialise normally."""
        result = render_prompt("#item", SIMPLE_TASK)
        data = json.loads(result)
        assert "cli" not in data
        assert data["task_no"] == "T-1"

    def test_item_appears_multiple_times(self):
        template = "#item\n---\n#item"
        result = render_prompt(template, SIMPLE_TASK)
        parts = result.split("\n---\n")
        assert len(parts) == 2
        assert json.loads(parts[0]) == json.loads(parts[1])

    def test_item_is_valid_json(self):
        result = render_prompt("#item", SIMPLE_TASK)
        data = json.loads(result)
        assert isinstance(data, dict)


class TestRenderPromptEdgeCases:
    def test_empty_template(self):
        assert render_prompt("", SIMPLE_TASK) == ""

    def test_no_placeholders(self):
        template = "No placeholders here."
        assert render_prompt(template, SIMPLE_TASK) == template

    def test_mixed_placeholders(self):
        template = "# {{task_no}}\n{{description}}\n\n#item"
        result = render_prompt(template, SIMPLE_TASK)
        assert "T-1" in result
        assert "Fix the authentication issue" in result
        parsed = json.loads(result.split("\n\n")[1])
        assert parsed["task_no"] == "T-1"

    def test_empty_task_dict(self):
        result = render_prompt("{{missing}}", {})
        assert result == ""

    def test_none_value_becomes_string_none(self):
        task = {"depends_on": None}
        result = render_prompt("{{depends_on}}", task)
        assert result == "None"
