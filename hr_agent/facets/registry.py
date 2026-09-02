"""Реестр фасет: фасет = MCP-тул + аргументы + whitelist полей (или ручная цепочка fetch)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from hr_agent.facets import projections as pj
from hr_agent.facets.mcp import McpCaller


class FacetError(Exception):
    """Фасет нельзя выполнить: не хватает ключа или данных для цепочки."""


@dataclass(frozen=True)
class FacetContext:
    today: date
    employee_id: str | None = None  # целевой сотрудник (табельный без нулей), уже прошедший guard
    person_id: str | None = None
    item_id: str | None = None  # курс
    keys: Mapping[str, Any] = field(default_factory=dict)  # number, request_id, activity_id, vac_num...


Fetch = Callable[[FacetContext, McpCaller], Awaitable[Any]]
Args = Callable[[FacetContext], dict[str, Any]]


def _no_args(_ctx: FacetContext) -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class FacetSpec:
    name: str
    description: str  # на языке инструкций, показывается модели
    tool: str = ""  # простой фасет: один MCP-тул
    args: Args = _no_args
    keep: tuple[str, ...] = ()  # whitelist полей после очистки; пусто — все
    fetch: Fetch | None = None  # цепочка или нестандартный ответ вместо tool
    needs_person: bool = False  # course: требует guard и person_id


@dataclass(frozen=True)
class EntitySpec:
    name: str
    description: str
    facets: tuple[FacetSpec, ...]

    def names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.facets)

    def select(self, names: Sequence[str]) -> list[FacetSpec]:
        by_name = {f.name: f for f in self.facets}
        return [by_name[n] for n in dict.fromkeys(names)]


def require(value: Any, what: str) -> Any:
    if value is None or value == "":
        raise FacetError(f"не указан {what}")
    return value


def _employee(ctx: FacetContext) -> dict[str, Any]:
    return {"employee_id": require(ctx.employee_id, "employee_id")}


def _person(ctx: FacetContext) -> dict[str, Any]:
    return {"person_id": require(ctx.person_id, "person_id")}


def _item(ctx: FacetContext) -> dict[str, Any]:
    return {"item_id": require(ctx.item_id, "item_id")}


def _person_item(ctx: FacetContext) -> dict[str, Any]:
    return {**_person(ctx), **_item(ctx)}


def _key(name: str) -> Args:
    return lambda ctx: {name: require(ctx.keys.get(name), name)}


# --------------------------------------------------------------------------- #
# Фасеты с цепочками и нестандартными ответами
# --------------------------------------------------------------------------- #

CONTACT_SEGMENTS = ("J.CONTACTS.EXTERNALEMAIL", "J.CONTACTS.INTEROFFICEEMAIL", "J.CONTACTS.COMPANYEMAIL")


def profile(segment_type: str, keep: tuple[str, ...] = (), list_key: str | None = None) -> Fetch:
    """Сегмент person_profile: data сегмента (или список data[list_key]) с whitelist полей."""

    async def fetch(ctx: FacetContext, mcp: McpCaller) -> Any:
        raw = await mcp.call("person_profile", {**_employee(ctx), "segments_raw": segment_type})
        data = pj.segment(raw, segment_type)
        if data is None:
            return None
        return pj.pick(pj.clean(data[list_key] if list_key else data), keep)

    return fetch


def people(tool: str) -> Fetch:
    """Список людей (HRBP, подчинённые) из ответа оргструктуры по person_id."""

    async def fetch(ctx: FacetContext, mcp: McpCaller) -> list[dict[str, Any]]:
        return pj.people(await mcp.call(tool, _person(ctx)))

    return fetch


async def _fetch_contacts(ctx: FacetContext, mcp: McpCaller) -> dict[str, Any]:
    raw = await mcp.call("person_profile", {**_employee(ctx), "segments_raw": "|".join(CONTACT_SEGMENTS)})
    return {seg: (pj.segment(raw, seg) or {}).get("value") for seg in CONTACT_SEGMENTS}


async def _fetch_org_chain(ctx: FacetContext, mcp: McpCaller) -> list[dict[str, Any]]:
    positions = pj.unwrap(await mcp.call("org_structure_user_info", _person(ctx))) or []
    if not positions:
        return []
    vertices = pj.unwrap(await mcp.call("org_structure_vertex_position", {"position_id": positions[0]["id"]}))
    return pj.org_chain(positions[0], vertices or [])


async def _fetch_assignment_requirements(ctx: FacetContext, mcp: McpCaller) -> dict[str, Any] | None:
    assignments = pj.unwrap(await mcp.call("assignment", {**_person_item(ctx), **_employee(ctx)})) or []
    match = next((a for a in assignments if a.get("itemId") == ctx.item_id), None)
    if not match:
        return None
    rows = pj.unwrap(await mcp.call("assignments_requirement", {"assignment_id": str(match["id"])})) or []
    return {"assignmentId": match["id"], "selfCancel": rows[0].get("selfCancel") if rows else None}


async def _fetch_publications(ctx: FacetContext, mcp: McpCaller) -> Any:
    if publication_id := ctx.keys.get("publication_id"):
        return pj.clean(await mcp.call("publication_info", {"publication_id": publication_id}))
    job_requisition_id = require(ctx.keys.get("job_requisition_id"), "publication_id или job_requisition_id")
    return pj.clean(
        await mcp.call("publication_info_by_job_requisition_id", {"job_requisition_id": job_requisition_id})
    )


# --------------------------------------------------------------------------- #
# Сущности: FacetSpec(name, description, tool, args, keep) либо fetch=...
# --------------------------------------------------------------------------- #
# fmt: off

EMPLOYEE = EntitySpec(
    name="employee",
    description=(
        "Данные о сотруднике из HR-сервисов. По умолчанию — текущий пользователь; "
        "for_employee_id — табельный номер подчинённого (данные других сотрудников недоступны). "
        "Запрашивай сразу все фасеты, нужные по инструкции."
    ),
    facets=(
        FacetSpec("basic", "стаж (лет, месяцев, дней), дата приёма, статус, категория персонала, испытательный срок",
                  fetch=profile("J.BASIC", ("hireDate", "lengthOfServiceYears", "lengthOfServiceMonth", "lengthOfServiceDays",
                                            "status", "categoryPerson", "probationStatus", "probationDateEnd"))),
        FacetSpec("position", "грейд (разряд), должность, подразделение, функциональный блок, уровень менеджмента",
                  fetch=profile("J.POSITION", ("grade", "gradeLevel", "fullName", "kostlName", "funcBlock", "positionId",
                                               "managementLevel"), list_key="position")),
        FacetSpec("contacts", "электронные адреса сотрудника", fetch=_fetch_contacts),
        FacetSpec("org_chain", "цепочка подразделений от банка до подразделения сотрудника и его позиция", fetch=_fetch_org_chain),
        FacetSpec("hrbp", "HR-бизнес-партнёр сотрудника: имя, табельный номер, позиция", fetch=people("org_structure_hrbp_info")),
        FacetSpec("subordinates", "подчинённые сотрудника: имя, табельный номер, позиция", fetch=people("org_structure_subordinate")),
        FacetSpec("is_chief", "является ли руководителем и какие подразделения в подчинении", "is_chief", _employee),
        FacetSpec("insurance", "страховые компании ДМС и НС, город сотрудника, программа ДМС", "get_health_company_name", _person,
                  ("insurance", "city", "location", "programType", "insuranceTypeDms")),
        FacetSpec("schedule", "график работы (вид графика)", "schedule_info", _employee, ("WrktmKind", "WrktmKindText", "DateReq")),
        FacetSpec("events", "кадровые мероприятия и отсутствия: вид, код вида, даты начала и окончания", "user_events_info", _employee),
        FacetSpec("absence_limits", "лимиты отпусков: вид отпуска, всего, использовано, остаток", "absence_limit", _employee,
                  ("LimId", "LimShort", "LimAnzhl", "LimKverb", "LimRest", "LimRestText", "DateReqBeg", "DateReqEnd")),
        FacetSpec("requests", "заявки (запросы) сотрудника в ЕАСУП за 45 дней: номер, статус, дата, код подтипа",
                  "user_request_info", _employee),
        FacetSpec("sicklists", "больничные листы: периоды", "sicklist_info", _employee),
        FacetSpec("access_groups", "группы доступа сотрудника", "authorization_groups", _person, ("group",)),
        FacetSpec("assignments", "назначенные курсы: название, статус, срок", "assignment",
                  lambda c: {**_person(c), "item_id": "", **_employee(c)},
                  ("id", "itemId", "itemName", "itemTypeDisplayName", "status", "statusDisplayName", "deadLine", "mandatory")),
        FacetSpec("learning_requests", "заявки на внешнее обучение: номер, название, статус", "learning_requests", _person),
        FacetSpec("recruiter_role", "является ли сотрудник рекрутером, группы рекрутера", "recruiter", _person),
    ),
)

COURSE = EntitySpec(
    name="course",
    description=(
        "Курс (учебный материал): укажи name (название, поиск в каталоге) или item_id. "
        "Фасеты availability, progress, history, onsite_registrations, assignment_requirements "
        "считаются для текущего пользователя или подчинённого (for_employee_id)."
    ),
    facets=(
        FacetSpec("catalog", "поиск курса в каталоге по названию: id, название, тип, статус", "item_ids_by_course_names",
                  lambda c: {"course_name": require(c.keys.get("name"), "name")}, ("id", "name", "type", "status", "description", "duration")),
        FacetSpec("availability", "доступен ли курс сотруднику", "course_available", _person_item, ("id", "name", "personOpt"),
                  needs_person=True),
        FacetSpec("progress", "прогресс сотрудника по курсу: пройден, просмотрен, процент", "course_progress", _person_item,
                  ("complete", "viewed", "opened", "assigned", "available", "contentState"), needs_person=True),
        FacetSpec("history", "история прохождения курса сотрудником: статус, сдан ли, дата завершения", "learning_history",
                  _person_item, ("itemName", "status", "passed", "completedAt"), needs_person=True),
        FacetSpec("tags", "теги курса", "item_tag", _item),
        FacetSpec("onsite_registrations", "регистрации сотрудника на очные мероприятия курса", "onsite_activities_registrations",
                  _person_item, needs_person=True),
        FacetSpec("assignment_requirements", "назначен ли курс сотруднику и можно ли отменить назначение самостоятельно",
                  fetch=_fetch_assignment_requirements, needs_person=True),
    ),
)

HR_REQUEST = EntitySpec(
    name="hr_request",
    description="Заявка (запрос) в ЕАСУП по номеру (8 цифр).",
    facets=(
        FacetSpec("status", "статус заявки ЕАСУП (TextStatus)", "user_request_info_by_number",
                  lambda c: {"number_req": require(c.keys.get("number"), "number")}),
    ),
)

LEARNING_REQUEST = EntitySpec(
    name="learning_request",
    description="Заявка на внешнее обучение по идентификатору.",
    facets=(
        FacetSpec("info", "заявка на обучение: статус, программа, провайдер, даты, стоимость, история согласования",
                  "learning_request_info", _key("request_id")),
    ),
)

ONSITE_ACTIVITY = EntitySpec(
    name="onsite_activity",
    description="Очное мероприятие по идентификатору.",
    facets=(
        FacetSpec("info", "информация о мероприятии: даты начала и окончания", "onsite_activities_information", _key("activity_id")),
    ),
)

VACANCY = EntitySpec(
    name="vacancy",
    description="Вакансия, публикация, отклик и профиль должности по их идентификаторам.",
    facets=(
        FacetSpec("job", "вакансия по номеру vac_num", "job_info", lambda c: {"vac_num": int(require(c.keys.get("vac_num"), "vac_num"))}),
        FacetSpec("publications", "публикации вакансии по publication_id или job_requisition_id", fetch=_fetch_publications),
        FacetSpec("application", "отклик на вакансию по job_application_id", "job_application", _key("job_application_id")),
        FacetSpec("job_profile", "профиль должности по position_id", "job_profile", _key("position_id")),
    ),
)

# fmt: on

ENTITIES: tuple[EntitySpec, ...] = (EMPLOYEE, COURSE, HR_REQUEST, LEARNING_REQUEST, ONSITE_ACTIVITY, VACANCY)
