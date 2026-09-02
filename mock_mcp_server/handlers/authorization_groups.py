"""Моковые тулы сервиса авторизации (группы доступа)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="authorization_groups",
        description=(
            "Группы доступа сотрудника. Вход: person_id (UUID). В data — список: group.identifier, "
            "group.description, validFrom, validTo. Пустой data — групп нет."
        ),
    )
    async def authorization_groups(person_id: str) -> dict:
        return data.get_user_groups(person_id=person_id)
