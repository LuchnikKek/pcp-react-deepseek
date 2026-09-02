"""Регистрация моковых MCP-тулов по группам backend-сервисов."""

from __future__ import annotations

from fastmcp import FastMCP

from . import (
    assignment,
    authorization_groups,
    catalog,
    easup,
    health,
    id_mapper,
    job_profile,
    learning_history,
    learning_requests,
    onsite_activities,
    organisation_structure,
    person_profile,
    recruitment,
    recruitment_publication,
)

_MODULES = (
    assignment,
    authorization_groups,
    catalog,
    easup,
    health,
    id_mapper,
    job_profile,
    learning_history,
    learning_requests,
    onsite_activities,
    organisation_structure,
    person_profile,
    recruitment,
    recruitment_publication,
)


def register_all(mcp: FastMCP) -> None:
    """Регистрирует все моковые тулы на переданном FastMCP-приложении."""
    for module in _MODULES:
        module.register(mcp)
