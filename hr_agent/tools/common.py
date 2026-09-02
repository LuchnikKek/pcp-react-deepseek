"""Общее для тулов: JSON-ответ и обновление state через Command."""

from __future__ import annotations

import json
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command


def to_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def reply(runtime: ToolRuntime, payload: Any, update: dict[str, Any] | None = None) -> str | Command:
    """Результат тула как JSON-строка; если есть update — вместе с обновлением state."""
    text = to_json(payload)
    if not update:
        return text
    return Command(update={**update, "messages": [ToolMessage(content=text, tool_call_id=runtime.tool_call_id)]})
