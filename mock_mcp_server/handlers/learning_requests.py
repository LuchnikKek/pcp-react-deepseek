"""Моковые тулы сервиса заявок на обучение (learning_requests)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="learning_requests",
        description=(
            "Активные заявки сотрудника на внешнее обучение. Вход: person_id (UUID). В data — заявки: requestId, "
            "name, status, createDate, data.programName, data.provider, data.cost. Пустой data — заявок нет."
        ),
    )
    async def learning_requests(person_id: str) -> dict:
        return data.get_learning_requests_by_person_id(person_id=person_id)

    @mcp.tool(
        name="learning_request_info",
        description=(
            "Заявка на обучение по id. Вход: request_id (requestId из тула learning_requests). В data[0]: "
            "request (id, name, state, template.displayName, assignee), report (programName, provider, "
            "educationStartDate, educationEndDate, cost, learningGoal), history. Ошибка — заявка не найдена."
        ),
    )
    async def learning_request_info(request_id: str) -> dict:
        return data.get_learning_request(request_id=request_id)
