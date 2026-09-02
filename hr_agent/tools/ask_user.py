"""Вопрос пользователю через interrupt (ARCHITECTURE §5.2, валидация §10).

При возобновлении код тула до interrupt() выполняется повторно, поэтому до него только чистая проверка аргументов.
"""

from __future__ import annotations

from langchain.tools import tool
from langgraph.types import interrupt

MAX_OPTIONS = 6


@tool(
    "ask_user",
    description=(
        "Задать сотруднику один уточняющий вопрос и получить его ответ. "
        f"options — варианты ответа (до {MAX_OPTIONS}), если уместно. Один вопрос за ход."
    ),
)
async def ask_user(question: str, options: list[str] | None = None) -> str:
    if not question.strip():
        return "Ошибка: вопрос пустой. Сформулируй вопрос и вызови ask_user снова."
    if options is not None and len(options) > MAX_OPTIONS:
        return f"Ошибка: вариантов больше {MAX_OPTIONS}. Сократи список и вызови ask_user снова."
    return interrupt({"question": question, "options": options})
