import pytest
from fastmcp.exceptions import ToolError

from hr_agent.facets.mcp import McpClient
from tests.conftest import EMPLOYEE_ID, PERSON_ID


async def test_dict_result(mcp: McpClient) -> None:
    raw = await mcp.call("schedule_info", {"employee_id": EMPLOYEE_ID})
    assert raw["d"]["Pernr"] == "01655480"


async def test_bare_list_result(mcp: McpClient) -> None:
    raw = await mcp.call("get_id_mapper_person_id", {"employee_id": EMPLOYEE_ID})
    assert isinstance(raw, list)
    assert raw[0]["response"][0]["value"] == PERSON_ID


async def test_not_found_raises_tool_error_with_reason(mcp: McpClient) -> None:
    with pytest.raises(ToolError, match="не найден"):
        await mcp.call("schedule_info", {"employee_id": "0"})
