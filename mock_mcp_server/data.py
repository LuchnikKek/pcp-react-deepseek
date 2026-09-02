"""Данные мокового MCP-сервера: загрузка фикстуры и lookup-хелперы.

Каждый хелпер возвращает **тело ответа backend-сервиса** ровно в том виде, в каком его отдаёт
реальный сервис (реальные ответы дев-стенда из ``fixtures/real_data_fixtures.json``, ключи вида
``"service:arg[:arg]"`` — как в ``tools/collect_real_data.py``).

Семантика «пусто vs ошибка»:

- запрос-коллекция (назначения, история, заявки, группы...) — пустой ``data`` допустимое
  значение, хелпер возвращает пустое тело по формату сервиса;
- запрос по ключу одной сущности (табельный номер, person_id, request_id...) — если сущности
  нет в данных, хелпер бросает :class:`NotFound`; FastMCP превращает её в ошибку тула с этим
  текстом, и агент видит причину, а не пустой ответ.

Каноническая связка ``employee_id <-> person_id`` берётся из раздела ``assignment`` и
переиспользуется во всех API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp.exceptions import ToolError


class NotFound(ToolError):
    """Сущность по запрошенному ключу отсутствует в данных мока."""


# --------------------------------------------------------------------------- #
# Загрузка реальных тел со стенда.
# --------------------------------------------------------------------------- #
_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "real_data_fixtures.json"


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Не найдена фикстура мокового MCP-сервера: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


_FIX: dict[str, Any] = _load_fixture(_FIXTURE_PATH)


def _fix(*parts: Any) -> Any:
    """Достаёт реальное тело из фикстуры по ``"service:arg"``-ключам (None, если нет)."""
    return _FIX.get(":".join(str(p) for p in parts))


# --------------------------------------------------------------------------- #
# Справочники: персоны и табельные номера.
# --------------------------------------------------------------------------- #
PERSONS = {
    # «Известный» сценарий: 2 активных назначения.
    "person_with_data": "9f219670-8655-4aab-a7b3-fdcf4e732ac6",
    # «Пустой» сценарий: 0 активных назначений.
    "person_empty": "4cccf617-0447-4d50-b90b-ae45096104b9",
    # Персона с 3 активными назначениями.
    "person_3_assignments": "3339552b-012b-4302-b331-129229c58eee",
    # Ещё одна персона без активных назначений.
    "person_0_assignments_2": "54dcb12a-4e27-415f-aead-30c4f0cb6868",
    # Персоны каталога.
    "person_catalog_a": "b7ca0d52-18f8-4771-9b1d-6025e6f03a29",
    "person_catalog_b": "762275f2-aea0-4c06-a31e-521e40c383ea",
    # Персоны раздела health.
    "person_health_1": "4482cbc6-05bf-43cb-9542-5b6a2b71acfb",
    "person_health_nodms": "7d365279-d209-4e09-bdf2-55b2a1e65f07",
    "person_health_2": "30e7c92e-ee1b-4dd7-aaa6-0ca348c63b2b",
    "person_health_3": "661ac345-b4d3-4b35-8bf7-23814af7bcce",
    "person_health_4": "d38252c9-0ac4-4d7c-b864-516bf8cfbdbd",
    "person_health_5": "585e65dc-7e43-48ab-818e-6dd2bf9c644e",
    "person_health_6": "dadcea6e-ff19-4156-8ff0-9599053c24e3",
}

EMPLOYEES = {
    "employee_with_data": "1655480",
    "employee_empty": "5581690",
    "employee_3_assignments": "4441",
    "employee_0_assignments_2": "10000543",
}

# Каноническая связка UUID <-> табельный (assignment / id_mapper / person_profile).
PERSON_TO_EMPLOYEE = {
    PERSONS["person_with_data"]: EMPLOYEES["employee_with_data"],
    PERSONS["person_empty"]: EMPLOYEES["employee_empty"],
    PERSONS["person_3_assignments"]: EMPLOYEES["employee_3_assignments"],
    PERSONS["person_0_assignments_2"]: EMPLOYEES["employee_0_assignments_2"],
}

# --------------------------------------------------------------------------- #
# Каталог: реальные item_id курсов.
# --------------------------------------------------------------------------- #
COURSE_A1 = "caef115d-f7b0-41bc-88d8-5be35d3782cb"
COURSE_A2 = "d7679660-1d8e-4027-8504-8af10a709334"
COURSE_B1 = "bb708aae-94e9-4b3d-83b8-ca387df02e61"
COURSE_B2 = "03abd3f2-a9a0-4fa4-b493-bad2bd38649d"
COURSE_FF = "0f48be8a-4fcf-40b2-b51f-da894969ce59"


def _build_course_index() -> dict[str, str]:
    """item_id -> имя курса из реальных тел ``catalog:*`` / ``catalog_page:*``."""
    index: dict[str, str] = {}
    for key, body in _FIX.items():
        if not key.startswith(("catalog_page:", "catalog:")):
            continue
        for item in (body or {}).get("data", []):
            if item.get("id") and item.get("name"):
                index.setdefault(item["id"], item["name"])
    return index


_COURSE_NAMES: dict[str, str] = _build_course_index()

# COURSES: имя курса -> реальный item_id.
COURSES: dict[str, str] = {name: iid for iid, name in _COURSE_NAMES.items()}


# --------------------------------------------------------------------------- #
# assignment
# --------------------------------------------------------------------------- #


def get_assignments(person_id: str) -> dict[str, Any]:
    """GET /assignments: активные назначения персоны.

    Назначения в реальном сервисе привязаны к персоне, а не к конкретному курсу,
    поэтому тело берётся по ``assignment:{person_id}``.
    """
    body = _fix("assignment", person_id)
    if isinstance(body, dict):
        return body
    return {"totalElements": 0, "totalPages": 1, "page": 0, "success": True, "data": []}


def get_assignments_requirement(ids: list[str]) -> dict[str, Any]:
    """GET /assignments/requirement."""
    out: dict[str, Any] = {"data": []}
    for aid in ids:
        req = _fix("assignment_requirement", aid)
        if isinstance(req, dict):
            out["data"].extend(req.get("data", []))
        elif req:
            out["data"].append(req)
    return out


# --------------------------------------------------------------------------- #
# authorization
# --------------------------------------------------------------------------- #


def get_user_groups(person_id: str) -> dict[str, Any]:
    """POST authorization/groups."""
    body = _fix("authorization", person_id)
    if isinstance(body, dict):
        return body
    return {"data": [], "meta": {"total": 0}}


# --------------------------------------------------------------------------- #
# catalog
# --------------------------------------------------------------------------- #


def get_catalog_item_by_name(item_name: str) -> dict[str, Any]:
    """POST catalog item/page по названию курса."""
    body = _fix("catalog", item_name)
    if isinstance(body, dict):
        return body
    item_id = COURSES.get(item_name)
    if item_id is not None:
        # Реальная страница каталога с этим курсом собрана по персоне — берём любую.
        for key, page in _FIX.items():
            if key.startswith("catalog_page:") and key.endswith(f":{item_id}") and isinstance(page, dict):
                return page
    return {"data": []}


def get_catalog_item_by_id(item_id: str, person_id: str) -> dict[str, Any]:
    """POST catalog item/page по id курса для персоны (course_available)."""
    body = _fix("catalog_page", person_id, item_id)
    if isinstance(body, dict):
        return body
    return {"data": []}


def get_item_progress(item_id: str, person_id: str) -> dict[str, Any]:
    """GET catalog item/{id}/person/{id}/progress."""
    body = _fix("catalog_progress", person_id, item_id)
    if isinstance(body, dict):
        return body
    return {"data": []}


def get_catalog_item_tags(item_id: str) -> dict[str, Any]:
    """GET catalog item/tag/{id}."""
    body = _fix("catalog_tags", item_id)
    if isinstance(body, dict):
        return body
    return {"data": []}


# --------------------------------------------------------------------------- #
# health
# --------------------------------------------------------------------------- #


def get_insurance_data(person_id: str) -> dict[str, Any]:
    """GET insurance-data: объект без обёртки."""
    body = _fix("health", person_id)
    if isinstance(body, dict):
        return body
    raise NotFound(f"Данные о страховании сотрудника {person_id} не найдены")


# --------------------------------------------------------------------------- #
# id_mapper
# --------------------------------------------------------------------------- #


def get_person_id_from_response(tn: str) -> list[dict[str, Any]]:
    """POST id-mapper keys: список без обёртки."""
    body = _fix("id_mapper", tn)
    if isinstance(body, list) and body:
        return body
    raise NotFound(f"Сотрудник с табельным номером {tn} не найден")


# --------------------------------------------------------------------------- #
# learning_history
# --------------------------------------------------------------------------- #


def get_person_learning_history(person_id: str, item_id: str) -> dict[str, Any]:
    """GET learning-history/history/person."""
    body = _fix("learning_history", person_id, item_id)
    if isinstance(body, dict):
        return body
    return {"data": []}


# --------------------------------------------------------------------------- #
# learning_requests
# --------------------------------------------------------------------------- #


def get_learning_requests_by_person_id(person_id: str) -> dict[str, Any]:
    """POST learning-requests/requests."""
    body = _fix("learning_requests", person_id)
    if isinstance(body, dict):
        return body
    return {
        "data": [],
        "pagination": {
            "extendedPageInfo": False,
            "page": 0,
            "pageCount": 0,
            "pageSize": 100,
            "sortColumns": [],
            "totalCount": 0,
        },
        "success": True,
    }


def get_learning_request(request_id: str) -> dict[str, Any]:
    """GET learning-requests/request/{id}."""
    body = _fix("learning_request", request_id)
    if isinstance(body, dict):
        return body
    raise NotFound(f"Заявка на обучение {request_id} не найдена")


# --------------------------------------------------------------------------- #
# onsite_activities
# --------------------------------------------------------------------------- #


def get_registrations(item_ids: list[str], person_ids: list[str]) -> dict[str, Any]:
    """POST onsite registrations."""
    for person_id in person_ids:
        for item_id in item_ids:
            body = _fix("registrations", person_id, item_id)
            if isinstance(body, dict):
                return body
    return {"data": []}


def get_activity_by_id(activity_id: str) -> dict[str, Any]:
    """POST onsite activities."""
    body = _fix("activities", activity_id)
    if isinstance(body, dict):
        return body
    raise NotFound(f"Очное мероприятие {activity_id} не найдено")


# --------------------------------------------------------------------------- #
# organisation_structure
# --------------------------------------------------------------------------- #


def get_org_vertex_by_person_id(person_id: str) -> dict[str, Any]:
    """POST org vertex/search по person_id."""
    body = _fix("org_vertex_person", person_id)
    if isinstance(body, dict) and body.get("data"):
        return body
    raise NotFound(f"Позиция сотрудника {person_id} в оргструктуре не найдена")


def get_org_vertex_by_position_id(position_id: str) -> dict[str, Any]:
    """POST org vertex/search по position_id."""
    body = _fix("org_vertex_position", position_id)
    if isinstance(body, dict) and body.get("data"):
        return body
    raise NotFound(f"Позиция {position_id} в оргструктуре не найдена")


def get_search_related_role(person_id: str) -> dict[str, Any]:
    """POST org person/searchRelatedRole (HRBP)."""
    body = _fix("org_hrbp", person_id)
    if isinstance(body, dict):
        return body
    return {"data": []}


def get_person_subordinate(person_id: str) -> dict[str, Any]:
    """GET org person/{id}/subordinate."""
    body = _fix("org_subordinate", person_id)
    if isinstance(body, dict):
        return body
    return {"data": []}


# --------------------------------------------------------------------------- #
# person_profile
# --------------------------------------------------------------------------- #


def post_segment_filter(types: list[str], employee_id: str) -> dict[str, Any]:
    """POST person-profile segment/filter: только запрошенные сегменты профиля."""
    body = _fix("person_profile", employee_id)
    if not isinstance(body, dict):
        raise NotFound(f"Сотрудник с табельным номером {employee_id} не найден")
    selected = [item for item in body.get("data", []) if item.get("type") in types]
    return {"data": selected}


# --------------------------------------------------------------------------- #
# recruitment — данных на стенде нет, поиск по ключу всегда «не найдено».
# --------------------------------------------------------------------------- #


def get_job_requisition(job_requisition_internal_id: int) -> dict[str, Any]:
    """GET job-requisition."""
    raise NotFound(f"Вакансия {job_requisition_internal_id} не найдена")


def get_job_application(job_application_id: str) -> dict[str, Any]:
    """GET job-application."""
    raise NotFound(f"Отклик {job_application_id} не найден")


def get_recruiter_info(person_id: str) -> dict[str, Any]:
    """GET recruiter/{person_id}."""
    body = _fix("recruiter", person_id)
    if isinstance(body, dict):
        return body
    return {"success": True, "data": {"employeeNumber": [], "profusersGroups": []}}


# --------------------------------------------------------------------------- #
# recruitment_publication / job_profile — данных на стенде нет.
# --------------------------------------------------------------------------- #


def get_publication(publication_id: str) -> dict[str, Any]:
    """GET publication: объект без обёртки."""
    raise NotFound(f"Публикация {publication_id} не найдена")


def get_publications_by_job_requisition_id(job_requisition_id: str) -> list[dict[str, Any]]:
    """GET publications: список без обёртки."""
    return []


def get_position_by_id(position_id: str) -> dict[str, Any]:
    """GET job-profile position: объект без обёртки."""
    raise NotFound(f"Профиль должности {position_id} не найден")


# --------------------------------------------------------------------------- #
# easup (OData, тело в {"d": ...}).
# --------------------------------------------------------------------------- #

_KNOWN_PERNRS = frozenset(EMPLOYEES.values())


def _prepare_pernr(pernr: str) -> str:
    """Приводит табельный номер к 8-значному SAP-формату, как easup_repo."""
    return str(pernr).zfill(8)


def _easup(kind: str, tn: str) -> dict[str, Any] | None:
    # в фикстуре ключи хранятся по исходному TN (без zfill); ищем и в 8-значном виде
    body = _fix(f"easup_{kind}", tn) or _fix(f"easup_{kind}", _prepare_pernr(tn))
    return body if isinstance(body, dict) else None


def _known_pernr(tn: str) -> bool:
    return tn in _KNOWN_PERNRS or tn.lstrip("0") in _KNOWN_PERNRS


def get_schedule_info(pernr: str) -> dict[str, Any]:
    """OData ScheduleSet."""
    body = _easup("schedule", pernr)
    if body is not None:
        return body
    raise NotFound(f"Сотрудник с табельным номером {pernr} не найден")


def get_user_events_info(pernr: str) -> dict[str, Any]:
    """OData EventsSet."""
    return _easup("events", pernr) or {"d": {"results": []}}


def get_absence_limits(pernr: str) -> dict[str, Any]:
    """OData LimitsSet."""
    return _easup("absence_limits", pernr) or {"d": {"results": []}}


def get_user_request_info_by_filter(pernr: str) -> dict[str, Any]:
    """OData StatusReqByPernrSet."""
    return _easup("user_requests", pernr) or {"d": {"results": []}}


def get_user_request_info_by_num(request_number: str) -> dict[str, Any]:
    """OData StatusReqSet."""
    body = _easup("user_request", request_number)
    if body is not None:
        return body
    raise NotFound(f"Заявка ЕАСУП №{request_number} не найдена")


def is_chief(pernr: str) -> dict[str, Any]:
    """OData AsChiefSet (на стенде 403 — для известных сотрудников отдаём «не руководитель»)."""
    body = _easup("is_chief", pernr)
    if body is not None:
        return body
    if _known_pernr(pernr):
        return {"d": {"Chief": False, "ChiefToOrg": {"results": []}}}
    raise NotFound(f"Сотрудник с табельным номером {pernr} не найден")


def get_sick_list_info(pernr: str) -> dict[str, Any]:
    """OData SickListSet."""
    return _easup("sicklist", pernr) or {"d": {"results": []}}
