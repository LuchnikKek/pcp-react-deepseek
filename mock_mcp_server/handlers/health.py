"""Моковые тулы сервиса страхования (health)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="get_health_company_name",
        description=(
            "Страхование сотрудника: ДМС и НС. Вход: person_id (UUID). Поля: insurance.dms.name, "
            "insurance.ns.name, programType, city, insuranceTypeDms. Пустой insurance — страховки не оформлены. "
            "Ошибка — сотрудник не найден."
        ),
    )
    async def get_health_company_name(person_id: str) -> dict:
        return data.get_insurance_data(person_id=person_id)
