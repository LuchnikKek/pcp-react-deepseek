"""Моковые тулы сервиса публикаций вакансий (recruitment_publication)."""

from __future__ import annotations

from fastmcp import FastMCP

from mock_mcp_server import data


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="publication_info",
        description=("Публикация вакансии по id. Вход: publication_id. Ошибка — публикация не найдена."),
    )
    async def publication_info(publication_id: str) -> dict:
        return data.get_publication(publication_id=publication_id)

    @mcp.tool(
        name="publication_info_by_job_requisition_id",
        description=(
            "Публикации вакансии. Вход: job_requisition_id. Ответ — список публикаций. Пустой список — публикаций нет."
        ),
    )
    async def publication_info_by_job_requisition_id(job_requisition_id: str) -> list:
        return data.get_publications_by_job_requisition_id(job_requisition_id=job_requisition_id)
