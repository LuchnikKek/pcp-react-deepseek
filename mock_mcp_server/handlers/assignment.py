"""Моковые тулы сервиса назначений (assignment)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="assignment",
        description=(
            "Активные назначения курсов сотруднику. Вход: person_id (UUID), employee_id (табельный номер), "
            "item_id курса. В data — список назначений: id, itemId, itemName, status, statusDisplayName, "
            "deadLine, createDate. Пустой data — активных назначений нет."
        ),
    )
    async def assignment(person_id: str, item_id: str, employee_id: str) -> dict:
        return data.get_assignments(person_id=person_id)

    @mcp.tool(
        name="assignments_requirement",
        description=(
            "Условия назначения: может ли сотрудник сам отменить назначение. Вход: assignment_id "
            "(поле id из тула assignment). В data — список с полями id, selfCancel. Пустой data — условий нет."
        ),
    )
    async def assignments_requirement(assignment_id: str) -> dict:
        return data.get_assignments_requirement(ids=[assignment_id])
