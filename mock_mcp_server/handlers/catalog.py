"""Моковые тулы каталога курсов (catalog)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="item_ids_by_course_names",
        description=(
            "Поиск курса в каталоге по названию (по вхождению). Вход: course_name. В data — найденные курсы: "
            "id (item_id), name, type, status, description, duration. Пустой data — курса с таким названием нет."
        ),
    )
    async def item_ids_by_course_names(course_name: str) -> dict:
        return data.get_catalog_item_by_name(item_name=course_name)

    @mcp.tool(
        name="course_available",
        description=(
            "Доступен ли курс сотруднику в каталоге. Вход: person_id (UUID), item_id курса. В data — курс "
            "с полем personOpt (available, assigned, complete). Пустой data — курс сотруднику недоступен или не найден."
        ),
    )
    async def course_available(person_id: str, item_id: str) -> dict:
        return data.get_catalog_item_by_id(item_id=item_id, person_id=person_id)

    @mcp.tool(
        name="course_progress",
        description=(
            "Прогресс сотрудника по курсу. Вход: person_id (UUID), item_id курса. В data — запись с полями "
            "complete, viewed, opened, assigned, contentState. Пустой data — сотрудник курс не начинал "
            "или курс не найден."
        ),
    )
    async def course_progress(person_id: str, item_id: str) -> dict:
        return data.get_item_progress(item_id=item_id, person_id=person_id)

    @mcp.tool(
        name="item_tag",
        description=("Теги курса. Вход: item_id курса. В data — список строк-тегов. Пустой data — тегов нет."),
    )
    async def item_tag(item_id: str) -> dict:
        return data.get_catalog_item_tags(item_id=item_id)
