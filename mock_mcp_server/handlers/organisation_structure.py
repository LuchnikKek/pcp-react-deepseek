"""Моковые тулы сервиса оргструктуры (organisation_structure)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="org_structure_user_info",
        description=(
            "Позиция сотрудника в оргструктуре. Вход: person_id (UUID). В data — вершины: id (position_id), "
            "name (должность), type, validFrom, validTo, company. Ошибка — позиция сотрудника не найдена."
        ),
    )
    async def org_structure_user_info(person_id: str) -> dict:
        return data.get_org_vertex_by_person_id(person_id=person_id)

    @mcp.tool(
        name="org_structure_vertex_position",
        description=(
            "Цепочка подразделений вверх от позиции. Вход: position_id (id из org_structure_user_info). "
            "В data — вершины от позиции до верхнего уровня: id, name, type, parent_edge. Ошибка — позиция не найдена."
        ),
    )
    async def org_structure_vertex_position(position_id: str) -> dict:
        return data.get_org_vertex_by_position_id(position_id=position_id)

    @mcp.tool(
        name="org_structure_hrbp_info",
        description=(
            "HR-бизнес-партнёр сотрудника. Вход: person_id (UUID). В data — вершины HRBP: id, name, type, "
            "personEdges. Пустой data — HRBP не назначен."
        ),
    )
    async def org_structure_hrbp_info(person_id: str) -> dict:
        return data.get_search_related_role(person_id=person_id)

    @mcp.tool(
        name="org_structure_subordinate",
        description=(
            "Прямые подчинённые сотрудника. Вход: person_id (UUID). В data — вершины подчинённых: id, name, "
            "type, personEdges. Пустой data — подчинённых нет."
        ),
    )
    async def org_structure_subordinate(person_id: str) -> dict:
        return data.get_person_subordinate(person_id=person_id)
