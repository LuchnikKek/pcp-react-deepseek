"""Моковые тулы сервиса истории обучения (learning_history)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="learning_history",
        description=(
            "История прохождения курса сотрудником. Вход: person_id (UUID), item_id курса. В data — попытки: "
            "status, passed, completedAt, itemName, createDate. Пустой data — сотрудник курс не проходил."
        ),
    )
    async def learning_history(person_id: str, item_id: str) -> dict:
        return data.get_person_learning_history(person_id=person_id, item_id=item_id)
