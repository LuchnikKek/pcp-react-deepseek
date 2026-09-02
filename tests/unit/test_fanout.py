import asyncio
import time
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from hr_agent.facets.fanout import TIMEOUT_TEXT, run_facets
from hr_agent.facets.mcp import McpClient
from hr_agent.facets.registry import FacetContext, FacetSpec
from tests.conftest import TODAY


class FakeMcp:
    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        if tool == "bad":
            raise ToolError("Сотрудник не найден")
        if tool == "boom":
            raise RuntimeError("connection reset")
        return {"success": True, "data": [{"tool": tool, "__metadata": {}}]}


def _spec(name: str, tool: str) -> FacetSpec:
    return FacetSpec(name, name, tool)


async def test_one_failing_facet_does_not_break_others() -> None:
    specs = [_spec("ok", "fine"), _spec("bad", "bad"), _spec("boom", "boom")]
    result = await run_facets(specs, FacetContext(today=TODAY), FakeMcp())
    assert result == {
        "ok": [{"tool": "fine"}],
        "bad": {"error": "Сотрудник не найден"},
        "boom": {"error": "ошибка сервиса: connection reset"},
    }


def _slow_server() -> FastMCP:
    server = FastMCP("slow")

    @server.tool
    async def slow() -> dict[str, Any]:
        await asyncio.sleep(0.4)
        return {"data": ["slow"]}

    @server.tool
    async def fast() -> dict[str, Any]:
        return {"data": ["fast"]}

    return server


async def test_timeout_and_parallel_execution() -> None:
    server = _slow_server()
    async with McpClient(server, timeout=0.15) as mcp:
        result = await run_facets([_spec("fast", "fast"), _spec("slow", "slow")], FacetContext(today=TODAY), mcp)
    assert result == {"fast": ["fast"], "slow": {"error": TIMEOUT_TEXT}}

    async with McpClient(server, timeout=5) as mcp:
        started = time.perf_counter()
        result = await run_facets([_spec("a", "slow"), _spec("b", "slow")], FacetContext(today=TODAY), mcp)
        elapsed = time.perf_counter() - started
    assert result == {"a": ["slow"], "b": ["slow"]}
    assert elapsed < 0.7, "фасеты должны выполняться параллельно"
