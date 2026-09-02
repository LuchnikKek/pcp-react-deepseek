"""Моковые тулы сервиса очных мероприятий (onsite_activities)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="onsite_activities_registrations",
        description=(
            "Регистрации сотрудника на очные мероприятия курса. Вход: person_id (UUID), item_id курса. "
            "В data — регистрации: id, activityId, status. Пустой data — регистраций нет."
        ),
    )
    async def onsite_activities_registrations(person_id: str, item_id: str) -> dict:
        return data.get_registrations(item_ids=[item_id], person_ids=[person_id])

    @mcp.tool(
        name="onsite_activities_information",
        description=(
            "Очное мероприятие по id. Вход: activity_id (activityId из регистрации). В data — мероприятие: "
            "startDate, endDate. Ошибка — мероприятие не найдено."
        ),
    )
    async def onsite_activities_information(activity_id: str) -> dict:
        return data.get_activity_by_id(activity_id=activity_id)
