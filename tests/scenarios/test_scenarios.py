"""Сценарные тесты с реальным DeepSeek (ARCHITECTURE §11): TOML-сценарии против мокового MCP и БЗ из xlsx.

Запуск: uv run pytest -m llm  (нужен DEEPSEEK_API_KEY в окружении или .env). По умолчанию исключены через addopts.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.checkpoint.memory import InMemorySaver

from hr_agent.agent.build import RECURSION_LIMIT, build_agent, make_model
from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.turn import TurnResult, run_turn
from hr_agent.cli import trim
from hr_agent.config import load_dotenv
from hr_agent.facets.mcp import McpClient
from hr_agent.kb.xlsx import XlsxKb
from mock_mcp_server.server import build_app

pytestmark = pytest.mark.llm

REPO = Path(__file__).resolve().parents[2]
SCENARIO_DIR = Path(__file__).parent
EXPECT_KEYS = {"kind", "group", "options_count", "text_contains", "tools_called", "tools_not_called"}


@dataclass(frozen=True)
class Step:
    user: str
    expect: dict[str, Any]


@dataclass(frozen=True)
class Scenario:
    id: str
    employee_id: str
    steps: list[Step]
    person_id: str | None = None
    trace: list[str] = field(default_factory=list)


def load_scenarios() -> list[Scenario]:
    scenarios = []
    for path in sorted(SCENARIO_DIR.glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        steps = [Step(s["user"], s.get("expect", {})) for s in data["steps"]]
        for step in steps:
            unknown = set(step.expect) - EXPECT_KEYS
            assert not unknown, f"{path.name}: неизвестные ключи expect {unknown}"
        scenarios.append(Scenario(path.stem, data["employee_id"], steps, data.get("person_id")))
    return scenarios


SCENARIOS = load_scenarios()


def mismatches(expect: dict[str, Any], result: TurnResult, calls: list[str]) -> list[str]:
    problems = []
    kinds = expect.get("kind")
    if kinds is not None and result.kind not in ([kinds] if isinstance(kinds, str) else kinds):
        problems.append(f"kind: ожидался {kinds}, получен {result.kind}")
    if "group" in expect and result.kind == "ticket_offer" and result.group != expect["group"]:
        problems.append(f"group: ожидалась {expect['group']!r}, получена {result.group!r}")
    if "options_count" in expect and len(result.options or []) != expect["options_count"]:
        problems.append(f"options_count: ожидалось {expect['options_count']}, получено {result.options}")
    for fragment in expect.get("text_contains", []):
        if fragment.lower() not in result.text.lower():
            problems.append(f"text_contains: нет фрагмента {fragment!r}")
    for tool in expect.get("tools_called", []):
        if tool not in calls:
            problems.append(f"tools_called: не вызван {tool} (вызваны {calls})")
    for tool in expect.get("tools_not_called", []):
        if tool in calls:
            problems.append(f"tools_not_called: вызван {tool}")
    return problems


def describe(message: BaseMessage) -> str:
    if isinstance(message, AIMessage):
        parts = [f"[reasoning] {trim(str(r), 600)}" for r in [message.additional_kwargs.get("reasoning_content")] if r]
        parts += [f"[tool_call] {c['name']}({c['args']})" for c in message.tool_calls]
        return "\n".join(parts) or f"[text] {trim(message.text, 300)}"
    return f"[{message.type}] {trim(str(message.content), 300)}"


@pytest.fixture(scope="module")
def model() -> BaseChatModel:
    load_dotenv(REPO / ".env")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY не задан")
    return make_model()


@pytest.fixture(scope="module")
def kb() -> XlsxKb:
    return XlsxKb(REPO / "bz_cut.xlsx")


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
async def test_scenario(scenario: Scenario, model: BaseChatModel, kb: XlsxKb) -> None:
    config = {"configurable": {"thread_id": scenario.id}, "recursion_limit": RECURSION_LIMIT}
    async with McpClient(build_app(), timeout=10) as mcp:
        context = RuntimeContext(
            employee_id=scenario.employee_id,
            session_id=scenario.id,
            today=date.today(),
            mcp=mcp,
            kb=kb,
            person_id=scenario.person_id,
        )
        agent = build_agent(model, checkpointer=InMemorySaver())
        for number, step in enumerate(scenario.steps, 1):
            calls: list[str] = []

            def on_message(message: BaseMessage, calls: list[str] = calls) -> None:
                scenario.trace.append(describe(message))
                if isinstance(message, AIMessage):
                    calls += [c["name"] for c in message.tool_calls]

            scenario.trace.append(f"вы> {step.user}")
            result = await run_turn(agent, config=config, context=context, message=step.user, on_message=on_message)
            scenario.trace.append(f"агент: {result}")
            problems = mismatches(step.expect, result, calls)
            assert not problems, (
                f"{scenario.id}, шаг {number}:\n- "
                + "\n- ".join(problems)
                + "\n\nТрасса:\n"
                + "\n".join(scenario.trace)
            )
