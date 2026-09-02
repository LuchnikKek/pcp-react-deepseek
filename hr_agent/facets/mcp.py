"""Обёртка над fastmcp.Client: один метод call(tool, args) с таймаутом на вызов."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Protocol, runtime_checkable

from fastmcp import Client, FastMCP
from mcp.shared.exceptions import McpError

REQUEST_TIMEOUT = 408  # код McpError при истечении таймаута ожидания ответа


@runtime_checkable
class McpCaller(Protocol):
    async def call(self, tool: str, args: dict[str, Any]) -> Any: ...


class McpClient:
    """MCP-клиент: target — URL сервера или FastMCP-инстанс (in-memory для тестов)."""

    def __init__(self, target: str | FastMCP, timeout: float = 10.0) -> None:
        self._client = Client(target)
        self._timeout = timeout

    async def __aenter__(self) -> McpClient:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self._client.__aexit__(exc_type, exc, tb)

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        """Тело ответа тула (dict или list). Ошибка тула -> fastmcp ToolError, таймаут -> TimeoutError."""
        try:
            return (await self._client.call_tool(tool, args, timeout=self._timeout)).data
        except McpError as exc:
            if exc.error.code == REQUEST_TIMEOUT:
                raise TimeoutError(f"{tool}: {exc.error.message}") from exc
            raise
