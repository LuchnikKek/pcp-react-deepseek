"""Моковые тулы ЕАСУП (OData)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="schedule_info",
        description=(
            "График работы сотрудника на сегодня (ЕАСУП). Вход: employee_id (табельный номер). Поля d: "
            "WrktmKindText (вид графика), Pernr, DateReq. Ошибка — сотрудник не найден."
        ),
    )
    async def schedule_info(employee_id: str) -> dict:
        return data.get_schedule_info(pernr=employee_id)

    @mcp.tool(
        name="user_events_info",
        description=(
            "Кадровые мероприятия сотрудника с начала года (ЕАСУП). Вход: employee_id (табельный номер). "
            "В d.results — список мероприятий. Пустой results — мероприятий нет."
        ),
    )
    async def user_events_info(employee_id: str) -> dict:
        return data.get_user_events_info(pernr=employee_id)

    @mcp.tool(
        name="absence_limit",
        description=(
            "Лимиты отпусков сотрудника за текущий год (ЕАСУП). Вход: employee_id (табельный номер). "
            "В d.results — лимиты: LimShort (вид отпуска), LimAnzhl (всего дней), LimKverb (использовано), "
            "LimRest и LimRestText (остаток). Пустой results — лимитов нет."
        ),
    )
    async def absence_limit(employee_id: str) -> dict:
        return data.get_absence_limits(pernr=employee_id)

    @mcp.tool(
        name="user_request_info",
        description=(
            "Заявки сотрудника в ЕАСУП за последние 45 дней (отпуска, справки и т.п.). Вход: employee_id "
            "(табельный номер). В d.results — заявки со статусами. Пустой results — заявок нет."
        ),
    )
    async def user_request_info(employee_id: str) -> dict:
        return data.get_user_request_info_by_filter(pernr=employee_id)

    @mcp.tool(
        name="user_request_info_by_number",
        description=(
            "Статус заявки ЕАСУП по её номеру. Вход: number_req. Поле d.TextStatus. Ошибка — заявка не найдена."
        ),
    )
    async def user_request_info_by_number(number_req: str) -> dict:
        return data.get_user_request_info_by_num(request_number=number_req)

    @mcp.tool(
        name="is_chief",
        description=(
            "Является ли сотрудник руководителем (ЕАСУП). Вход: employee_id (табельный номер). Поля d: "
            "Chief (true/false), ChiefToOrg.results — подразделения в подчинении. Ошибка — сотрудник не найден."
        ),
    )
    async def is_chief(employee_id: str) -> dict:
        return data.is_chief(pernr=employee_id)

    @mcp.tool(
        name="sicklist_info",
        description=(
            "Больничные листы сотрудника за последние 45 дней (ЕАСУП). Вход: employee_id (табельный номер). "
            "В d.results — список больничных. Пустой results — больничных нет."
        ),
    )
    async def sicklist_info(employee_id: str) -> dict:
        return data.get_sick_list_info(pernr=employee_id)
