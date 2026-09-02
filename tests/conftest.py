"""Общие фикстуры: in-process мок MCP, фейковая БЗ, запуск тула через граф с ToolNode."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.state import HrAgentState
from hr_agent.facets.mcp import McpCaller, McpClient
from hr_agent.kb.fake import InMemoryKb
from hr_agent.kb.models import Instruction
from mock_mcp_server.server import build_app

EMPLOYEE_ID = "1655480"
PERSON_ID = "9f219670-8655-4aab-a7b3-fdcf4e732ac6"
EMPTY_EMPLOYEE_ID = "5581690"
SUBORDINATE_ID = "1652914"  # есть в org_structure_subordinate у 1655480
STRANGER_ID = "4441"  # известный сотрудник, но не подчинённый
COURSE_NAME = "Правила пожарной безопасности"
COURSE_ID = "0f48be8a-4fcf-40b2-b51f-da894969ce59"
TODAY = date(2026, 9, 2)

INSTRUCTIONS = [
    Instruction(
        id=48,
        question="Входит ли гигиена в стоматологию по ДМС?",
        type="API",
        topics=["ДМС Мое здоровье", "Программа ДМС"],
        text="Уточни тематику. Получи данные о стаже.",
        status="status_true",
    ),
    Instruction(
        id=99,
        question="Как записаться к психологу онлайн?",
        type="RAG",
        topics=["ДМС Мое здоровье", "Психологическая поддержка"],
        text="Записаться можно в приложении.",
        status="status_true",
    ),
    Instruction(
        id=7,
        question="Как изменить рабочую группу заявки по ДМС?",
        type="API",
        topics=["ДМС Мое здоровье"],
        text="Измени рабочую группу в SAP GUI.",
        status="status_false",
    ),
]


@pytest.fixture
async def mcp() -> AsyncIterator[McpClient]:
    async with McpClient(build_app(), timeout=5) as client:
        yield client


@pytest.fixture
def kb() -> InMemoryKb:
    return InMemoryKb(INSTRUCTIONS)


class CountingMcp:
    """Обёртка над McpCaller, запоминающая имена вызванных тулов."""

    def __init__(self, inner: McpCaller) -> None:
        self.inner = inner
        self.calls: list[str] = []

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        self.calls.append(tool)
        return await self.inner.call(tool, args)


def make_context(
    mcp: McpCaller,
    kb: InMemoryKb | None = None,
    employee_id: str = EMPLOYEE_ID,
    person_id: str | None = None,
) -> RuntimeContext:
    return RuntimeContext(
        employee_id=employee_id,
        session_id="s1",
        today=TODAY,
        mcp=mcp,
        kb=kb or InMemoryKb(INSTRUCTIONS),
        person_id=person_id,
    )


class ToolRunner:
    """Запускает один тул как ToolNode в графе с checkpointer'ом: видны Command-обновления и interrupt."""

    def __init__(self, tool: BaseTool, context: RuntimeContext) -> None:
        graph = StateGraph(HrAgentState, context_schema=RuntimeContext)
        graph.add_node("tools", ToolNode([tool]))
        graph.add_edge(START, "tools")
        graph.add_edge("tools", END)
        self.app = graph.compile(checkpointer=InMemorySaver())
        self.tool = tool
        self.context = context
        self.config = {"configurable": {"thread_id": "t1"}}
        self._n = 0

    async def invoke(self, args: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
        self._n += 1
        call = {"name": self.tool.name, "args": args, "id": f"call_{self._n}", "type": "tool_call"}
        payload = {"messages": [AIMessage(content="", tool_calls=[call])], **(state or {})}
        return await self.app.ainvoke(payload, config=self.config, context=self.context)

    async def resume(self, value: Any) -> dict[str, Any]:
        return await self.app.ainvoke(Command(resume=value), config=self.config, context=self.context)


def last_json(result: dict[str, Any]) -> Any:
    return json.loads(result["messages"][-1].content)
