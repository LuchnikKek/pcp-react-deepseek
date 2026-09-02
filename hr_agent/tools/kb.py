"""Тулы базы знаний: двухступенчатый поиск (ARCHITECTURE §5.1)."""

from __future__ import annotations

from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.state import HrAgentState
from hr_agent.kb.models import STATUS_FALSE
from hr_agent.tools.common import reply, to_json

Runtime = ToolRuntime[RuntimeContext, HrAgentState]


@tool(
    "search_instructions",
    description=(
        "Поиск инструкций в базе знаний по вопросу сотрудника. Возвращает до 10 заголовков: "
        "id, question, type (RAG / API / API_HARD), topics, score. Полный текст — через get_instruction."
    ),
)
async def search_instructions(runtime: Runtime, query: str) -> str:
    headers = await runtime.context.kb.search(query)
    return to_json([h.model_dump(exclude={"status"}) for h in headers if h.status != STATUS_FALSE])


@tool(
    "get_instruction",
    description=(
        "Полный текст одной инструкции по id из результатов search_instructions. "
        "Открывай только ту инструкцию, которая подходит по заголовку."
    ),
)
async def get_instruction(runtime: Runtime, id: int) -> str | Command:  # noqa: A002 — имя параметра из контракта
    instruction = await runtime.context.kb.get(id)
    if instruction is None or instruction.status == STATUS_FALSE:
        return to_json({"error": f"инструкция {id} не найдена"})
    update = {"active_instruction_id": id, "seen_instruction_ids": [id]}
    return reply(runtime, instruction.model_dump(exclude={"status"}), update)
