"""Моковые тулы сервиса рекрутмента (recruitment)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="job_info",
        description=("Вакансия по внутреннему номеру. Вход: vac_num. Ответ в data. Ошибка — вакансия не найдена."),
    )
    async def job_info(vac_num: int) -> dict:
        return data.get_job_requisition(job_requisition_internal_id=vac_num)

    @mcp.tool(
        name="job_application",
        description=("Отклик на вакансию по id. Вход: job_application_id. Ответ в data. Ошибка — отклик не найден."),
    )
    async def job_application(job_application_id: str) -> dict:
        return data.get_job_application(job_application_id=job_application_id)

    @mcp.tool(
        name="recruiter",
        description=(
            "Является ли сотрудник рекрутером. Вход: person_id (UUID). Поля data: employeeNumber (табельные "
            "номера рекрутера), profusersGroups (группы). Пустые списки — сотрудник не рекрутер."
        ),
    )
    async def recruiter(person_id: str) -> dict:
        return data.get_recruiter_info(person_id=person_id)
