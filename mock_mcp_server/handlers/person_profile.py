"""Моковые тулы сервиса профиля сотрудника (person_profile)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="person_profile",
        description=(
            "Сегменты профиля сотрудника. Вход: employee_id (табельный номер), segments_raw — коды сегментов "
            "через «|», например J.BASIC|J.POSITION|J.UNIT|J.CONTACTS.COMPANYEMAIL. В data — сегменты: type, "
            "personUuid, data (содержимое сегмента). Пустой data — запрошенных сегментов у сотрудника нет. "
            "Ошибка — сотрудник не найден."
        ),
    )
    async def person_profile(employee_id: str, segments_raw: str) -> dict:
        segments = [s.strip("\"' ") for s in segments_raw.split("|") if s.strip()]
        return data.post_segment_filter(types=segments, employee_id=employee_id)
