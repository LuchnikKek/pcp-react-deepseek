from hr_agent.facets.mcp import McpClient
from hr_agent.tools import get_instruction, search_instructions
from tests.conftest import ToolRunner, last_json, make_context


async def test_search_hides_status_false_and_status_field(mcp: McpClient) -> None:
    runner = ToolRunner(search_instructions, make_context(mcp))
    headers = last_json(await runner.invoke({"query": "ДМС записаться"}))
    assert [h["id"] for h in headers] == [48, 99]
    assert set(headers[0]) == {"id", "question", "type", "topics", "score"}


async def test_get_instruction_updates_state(mcp: McpClient) -> None:
    runner = ToolRunner(get_instruction, make_context(mcp))
    result = await runner.invoke({"id": 48})
    assert last_json(result)["text"].startswith("Уточни тематику")
    assert "status" not in last_json(result)
    assert result["active_instruction_id"] == 48
    assert result["seen_instruction_ids"] == [48]

    result = await runner.invoke({"id": 99})
    assert result["active_instruction_id"] == 99
    assert result["seen_instruction_ids"] == [48, 99]

    result = await runner.invoke({"id": 48})
    assert result["seen_instruction_ids"] == [48, 99]


async def test_get_instruction_not_found(mcp: McpClient) -> None:
    runner = ToolRunner(get_instruction, make_context(mcp))
    assert last_json(await runner.invoke({"id": 999})) == {"error": "инструкция 999 не найдена"}
    assert last_json(await runner.invoke({"id": 7})) == {"error": "инструкция 7 не найдена"}
