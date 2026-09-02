"""Выполнение фасет: один фасет = вызов MCP + проекция; все запрошенные — параллельно."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from fastmcp.exceptions import ToolError

from hr_agent.facets.mcp import McpCaller
from hr_agent.facets.projections import clean, pick, unwrap
from hr_agent.facets.registry import FacetContext, FacetError, FacetSpec

TIMEOUT_TEXT = "превышено время ожидания сервиса"


async def run_facet(spec: FacetSpec, ctx: FacetContext, mcp: McpCaller) -> Any:
    if spec.fetch:
        return await spec.fetch(ctx, mcp)
    return pick(clean(unwrap(await mcp.call(spec.tool, spec.args(ctx)))), spec.keep)


def error_text(exc: BaseException) -> str:
    if isinstance(exc, FacetError | ToolError):
        return str(exc)
    if isinstance(exc, TimeoutError):
        return TIMEOUT_TEXT
    return f"ошибка сервиса: {exc}"


async def run_facets(specs: Sequence[FacetSpec], ctx: FacetContext, mcp: McpCaller) -> dict[str, Any]:
    """{facet: data | {"error": text}}; ошибка одного фасета не ломает остальные."""
    results = await asyncio.gather(*(run_facet(spec, ctx, mcp) for spec in specs), return_exceptions=True)
    return {
        spec.name: {"error": error_text(result)} if isinstance(result, BaseException) else result
        for spec, result in zip(specs, results, strict=True)
    }
