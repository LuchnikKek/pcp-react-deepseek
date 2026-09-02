"""Identity guard: связка employee_id <-> person_id (кэш в state) и проверка «свой или подчинённый»."""

from __future__ import annotations

from typing import Any, TypedDict

from hr_agent.facets.mcp import McpCaller
from hr_agent.facets.projections import iter_person_edges, strip_leading_zeros, unwrap
from hr_agent.facets.registry import FacetError

ACCESS_DENIED = "нет доступа к данным этого сотрудника"


class Identity(TypedDict):
    """Кэш на сессию: текущий пользователь и его подчинённые (employee_id -> person_id, грузятся лениво)."""

    employee_id: str
    person_id: str
    subordinates: dict[str, str] | None


class AccessDenied(Exception):
    pass


async def lookup_person_id(mcp: McpCaller, employee_id: str) -> str:
    rows: Any = await mcp.call("get_id_mapper_person_id", {"employee_id": employee_id})
    for row in rows or []:
        for item in row.get("response") or []:
            if item.get("key") == "PERSONID" and item.get("value"):
                return item["value"]
    raise FacetError(f"person_id для табельного номера {employee_id} не найден")


async def subordinate_map(mcp: McpCaller, person_id: str) -> dict[str, str]:
    raw = await mcp.call("org_structure_subordinate", {"person_id": person_id})
    out: dict[str, str] = {}
    for _vertex, edge in iter_person_edges(unwrap(raw) or []):
        employee_id = strip_leading_zeros((edge.get("data") or {}).get("employeeId"))
        pid = (edge.get("person") or {}).get("id")
        if employee_id and pid:
            out.setdefault(employee_id, pid)
    return out


async def ensure_identity(
    mcp: McpCaller,
    *,
    employee_id: str,
    person_id: str | None,
    identity: Identity | None,
    need_subordinates: bool,
) -> Identity:
    """Identity текущего пользователя: из кэша, если он про него; подчинённые — только когда нужны."""
    own = strip_leading_zeros(employee_id) or employee_id
    if identity is None or identity["employee_id"] != own:
        identity = Identity(employee_id=own, person_id=person_id or await lookup_person_id(mcp, own), subordinates=None)
    if need_subordinates and identity["subordinates"] is None:
        identity = Identity(**{**identity, "subordinates": await subordinate_map(mcp, identity["person_id"])})
    return identity


def pick_target(identity: Identity, for_employee_id: str | None) -> tuple[str, str]:
    """(employee_id, person_id) целевого сотрудника; чужой табельный -> AccessDenied."""
    target = strip_leading_zeros(for_employee_id)
    if target is None or target == identity["employee_id"]:
        return identity["employee_id"], identity["person_id"]
    person_id = (identity["subordinates"] or {}).get(target)
    if person_id is None:
        raise AccessDenied(ACCESS_DENIED)
    return target, person_id
