"""
Template rendering for task prompts.

Supports:
  - {{key}} — replaced with task[key] value
  - #item   — replaced with the full task JSON object
"""

import json
import re


def render_prompt(template: str, task: dict) -> str:
    """
    Render a prompt template by substituting placeholders with task data.

    Placeholder rules:
      1. {{key}}  — Replaced with str(task[key]). If the value is a dict/list,
                     it's serialized as indented JSON. Missing keys → empty string.
      2. #item    — Replaced with the entire task dict as a JSON string.

    Args:
        template: The prompt template string.
        task: A single task dict from the plan's tasks array.

    Returns:
        The rendered prompt string.
    """
    result = template

    # 1. Replace {{key}} placeholders
    def _replace_key(match: re.Match) -> str:
        key = match.group(1).strip()
        value = task.get(key, "")
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)

    result = re.sub(r"\{\{(\w+)\}\}", _replace_key, result)

    # 2. Replace #item with the full task JSON
    task_json = json.dumps(task, ensure_ascii=False, indent=2)
    result = result.replace("#item", task_json)

    return result
