"""Моковые тулы сервиса сопоставления идентификаторов (id_mapper)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="get_id_mapper_person_id",
        description=(
            "Получить person_id (UUID) сотрудника по табельному номеру. Вход: employee_id (табельный номер). "
            "Ответ — список; UUID лежит в [0].response[0].value. Ошибка — табельный номер не найден."
        ),
    )
    async def get_id_mapper_person_id(employee_id: str) -> list:
        return data.get_person_id_from_response(tn=employee_id)
