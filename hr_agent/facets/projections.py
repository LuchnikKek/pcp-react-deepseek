"""Проекция ответов MCP-тулов: снять обёртку, убрать служебные поля, нормализовать даты и табельные."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

SERVICE_KEYS = frozenset({"success", "pagination", "meta", "totalElements", "totalPages", "page", "__metadata"})
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T")
_SAP_DATE = re.compile(r"^\d{8}$")
_DATE_KEY = re.compile(r"date|begda|endda", re.IGNORECASE)


def norm_date(value: Any) -> Any:
    """ISO datetime / SAP YYYYMMDD -> YYYY-MM-DD; остальное как есть."""
    if isinstance(value, str):
        if _ISO_DATETIME.match(value):
            return value[:10]
        if _SAP_DATE.match(value):
            return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def strip_leading_zeros(employee_id: Any) -> str | None:
    text = "" if employee_id is None else str(employee_id).strip()
    return (text.lstrip("0") or "0") if text else None


def unwrap(raw: Any) -> Any:
    """Полезная часть тела: d.results / d (ЕАСУП) или data; тела без обёртки — как есть."""
    if isinstance(raw, Mapping):
        if "d" in raw:
            d = raw["d"] or {}
            return d["results"] if isinstance(d, Mapping) and "results" in d else d
        if "data" in raw:
            return raw["data"]
    return raw


def clean(obj: Any, key: str = "") -> Any:
    """Рекурсивно: без служебных ключей, Pernr без нулей, даты (ISO и SAP в полях-датах) в YYYY-MM-DD."""
    if isinstance(obj, Mapping):
        return {k: clean(v, k) for k, v in obj.items() if k not in SERVICE_KEYS}
    if isinstance(obj, list):
        return [clean(v, key) for v in obj]
    if isinstance(obj, str):
        if key == "Pernr":
            return strip_leading_zeros(obj)
        if _ISO_DATETIME.match(obj) or (_SAP_DATE.match(obj) and _DATE_KEY.search(key)):
            return norm_date(obj)
    return obj


def pick(obj: Any, keys: Sequence[str]) -> Any:
    """Оставить только keys у объекта или у каждого элемента списка; пустой keys — без фильтра."""
    if not keys:
        return obj
    if isinstance(obj, Mapping):
        return {k: obj[k] for k in keys if k in obj}
    if isinstance(obj, list):
        return [pick(item, keys) for item in obj]
    return obj


def segment(raw: Any, segment_type: str) -> dict[str, Any] | None:
    """data сегмента person_profile нужного типа."""
    for item in unwrap(raw) or []:
        if item.get("type") == segment_type:
            return item.get("data") or {}
    return None


def iter_person_edges(vertices: list[dict[str, Any]]) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """(вершина, personEdge) по вершинам оргструктуры и их children рекурсивно."""
    for vertex in vertices:
        for edge in vertex.get("personEdges") or []:
            yield vertex, edge
        yield from iter_person_edges(vertex.get("children") or [])


def people(raw: Any) -> list[dict[str, Any]]:
    """Люди из ответа оргструктуры (HRBP, подчинённые): ФИО, табельный, позиция, подразделение."""
    out = []
    for vertex, edge in iter_person_edges(unwrap(raw) or []):
        person, data = edge.get("person") or {}, edge.get("data") or {}
        name = " ".join(p for p in (person.get("lastName"), person.get("firstName"), person.get("midName")) if p)
        out.append(
            {
                "fullName": name,
                "employeeId": strip_leading_zeros(data.get("employeeId")),
                "position": vertex.get("name"),
                "kostlName": data.get("kostlName"),
            }
        )
    return out


def org_chain(position: Mapping[str, Any], vertices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Вложенные children (банк -> ... -> подразделение) в плоский список плюс позиция сотрудника."""
    chain: list[dict[str, Any]] = []
    node: Mapping[str, Any] | None = vertices[0] if vertices else None
    while node:
        chain.append({"name": node.get("name"), "type": node.get("type")})
        children = node.get("children") or []
        node = children[0] if children else None
    chain.append({"name": position.get("name"), "type": position.get("type")})
    return chain
