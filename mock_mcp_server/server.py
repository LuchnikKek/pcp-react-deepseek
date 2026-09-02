"""Сборка FastMCP-приложения мокового сервера."""

from __future__ import annotations

from fastmcp import FastMCP

from .handlers import register_all

SERVER_NAME = "hr-agent-mock"

INSTRUCTIONS = (
    "MCP-сервер HR-сервисов банка. Тулы возвращают ответы backend-сервисов как есть: "
    "полезные данные лежат в поле data (для сервисов ЕАСУП — в d или d.results); "
    "поля success, pagination, meta, totalElements, totalPages, page, __metadata — служебные, "
    "не используй их. Сотрудник идентифицируется двумя ключами: employee_id — табельный номер, "
    "person_id — UUID; связать их можно тулом get_id_mapper_person_id. "
    "Пустой data означает «данных нет» (это нормальный ответ); если сущность по ключу не найдена, "
    "тул возвращает ошибку с причиной."
)


def build_app() -> FastMCP:
    """Создаёт и возвращает FastMCP-приложение со всеми зарегистрированными мок-тулами."""
    mcp = FastMCP(SERVER_NAME, instructions=INSTRUCTIONS)
    register_all(mcp)
    return mcp
