from pathlib import Path

import pytest

from hr_agent.facets.mcp import McpClient
from hr_agent.kb.models import STATUS_FALSE
from hr_agent.kb.xlsx import XlsxKb, tokenize
from hr_agent.tools import search_instructions
from tests.conftest import ToolRunner, last_json, make_context

XLSX = Path(__file__).resolve().parents[2] / "bz_cut.xlsx"


@pytest.fixture(scope="module")
def xlsx_kb() -> XlsxKb:
    return XlsxKb(XLSX)


def test_tokenize() -> None:
    assert tokenize("Входит ли гигиена, в ДМС?") == ["входит", "ли", "гигиена", "в", "дмс"]


async def test_loads_all_instructions(xlsx_kb: XlsxKb) -> None:
    row = await xlsx_kb.get(48)
    assert row is not None
    assert row.type == "API_HARD"
    assert row.topics == ["ДМС Мое здоровье", "Программа ДМС", "Стоматология"]
    assert row.status == "status_true"
    assert row.text.startswith("Последовательность действий")
    assert (await xlsx_kb.get(99)).type == "RAG"
    assert await xlsx_kb.get(999) is None
    assert len(xlsx_kb._items) == 112


async def test_search_ranks_relevant_question_first(xlsx_kb: XlsxKb) -> None:
    headers = await xlsx_kb.search("входит ли гигиена в стоматологию по ДМС?")
    assert headers and headers[0].id == 48
    assert len(headers) <= 10
    assert headers[0].score >= headers[-1].score
    assert await xlsx_kb.search("qwertyuiop") == []


async def test_search_returns_full_top_10_of_visible_rows(xlsx_kb: XlsxKb) -> None:
    headers = await xlsx_kb.search("изменить счёт для зачисления зарплаты")
    assert len(headers) == 10
    assert all(h.status != STATUS_FALSE for h in headers)


async def test_tool_hides_status_false_rows(xlsx_kb: XlsxKb, mcp: McpClient) -> None:
    hidden = {i.id for i in xlsx_kb._items.values() if i.status == STATUS_FALSE}
    assert hidden
    runner = ToolRunner(search_instructions, make_context(mcp, kb=xlsx_kb))
    headers = last_json(await runner.invoke({"query": "изменить рабочую группу заявки"}))
    assert headers
    assert hidden.isdisjoint(h["id"] for h in headers)
