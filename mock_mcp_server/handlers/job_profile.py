"""Моковые тулы сервиса профилей должностей (job_profile)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="job_profile",
        description=(
            "Профиль должности. Вход: position_id (id позиции из org_structure_user_info). Поля: status, "
            "publishedAt. Ошибка — профиль должности не найден."
        ),
    )
    async def job_profile(position_id: str) -> dict:
        return data.get_position_by_id(position_id=position_id)
