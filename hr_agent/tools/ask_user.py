"""Вопрос пользователю через interrupt (ARCHITECTURE §5.2).

При возобновлении код тула до interrupt() выполняется повторно, поэтому в теле только вызов interrupt.
"""

from __future__ import annotations

from langchain.tools import tool
from langgraph.types import interrupt


@tool(
    "ask_user",
    description=(
        "Задать сотруднику один уточняющий вопрос и получить его ответ. "
        "options — варианты ответа (до 6), если уместно. Один вопрос за ход."
    ),
)
async def ask_user(question: str, options: list[str] | None = None) -> str:
    return interrupt({"question": question, "options": options})
