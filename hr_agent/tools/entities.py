"""Тулы-сущности с фасетами (ARCHITECTURE §5.3): enum фасет и описание собираются из реестра."""

# Без `from __future__ import annotations`: Literal-типы фасет должны быть вычислены при импорте.

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Literal

from fastmcp.exceptions import ToolError
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.state import HrAgentState
from hr_agent.facets.fanout import run_facets
from hr_agent.facets.identity import ACCESS_DENIED, AccessDenied, ensure_identity, pick_target
from hr_agent.facets.projections import unwrap
from hr_agent.facets.registry import (
    COURSE,
    EMPLOYEE,
    HR_REQUEST,
    LEARNING_REQUEST,
    ONSITE_ACTIVITY,
    VACANCY,
    EntitySpec,
    FacetContext,
    FacetError,
    FacetSpec,
)
from hr_agent.tools.common import reply

Runtime = ToolRuntime[RuntimeContext, HrAgentState]


def facet_literal(entity: EntitySpec) -> Any:
    """Literal[...] из имён фасет: pydantic превращает его в enum в схеме тула."""
    return Literal[entity.names()]


def facet_description(entity: EntitySpec) -> str:
    lines = [entity.description, "", "Фасеты (facets):"]
    lines += [f"- {facet.name}: {facet.description}" for facet in entity.facets]
    return "\n".join(lines)


EmployeeFacet = facet_literal(EMPLOYEE)
CourseFacet = facet_literal(COURSE)
HrRequestFacet = facet_literal(HR_REQUEST)
LearningRequestFacet = facet_literal(LEARNING_REQUEST)
OnsiteActivityFacet = facet_literal(ONSITE_ACTIVITY)
VacancyFacet = facet_literal(VACANCY)


async def _run(
    runtime: Runtime,
    specs: Sequence[FacetSpec],
    *,
    guard: bool,
    for_employee_id: str | None = None,
    item_id: str | None = None,
    keys: Mapping[str, Any] | None = None,
) -> str | Command:
    """Guard (если нужен) -> fan-out -> JSON. После guard identity всегда сохраняется в state."""
    ctx = runtime.context
    facet_ctx = FacetContext(today=ctx.today, item_id=item_id, keys=keys or {})
    if not guard:
        return reply(runtime, await run_facets(specs, facet_ctx, ctx.mcp))
    try:
        identity = await ensure_identity(
            ctx.mcp,
            employee_id=ctx.employee_id,
            person_id=ctx.person_id,
            identity=runtime.state.get("identity"),
            need_subordinates=for_employee_id is not None,
        )
    except (ToolError, FacetError) as exc:
        return reply(runtime, {"error": str(exc)})
    update = {"identity": identity}
    try:
        employee_id, person_id = pick_target(identity, for_employee_id)
    except AccessDenied:
        return reply(runtime, {"error": ACCESS_DENIED}, update)
    facet_ctx = replace(facet_ctx, employee_id=employee_id, person_id=person_id)
    return reply(runtime, await run_facets(specs, facet_ctx, ctx.mcp), update)


@tool("employee", description=facet_description(EMPLOYEE))
async def employee(runtime: Runtime, facets: list[EmployeeFacet], for_employee_id: str | None = None) -> str | Command:
    return await _run(runtime, EMPLOYEE.select(facets), guard=True, for_employee_id=for_employee_id)


@tool("course", description=facet_description(COURSE))
async def course(
    runtime: Runtime,
    facets: list[CourseFacet],
    name: str | None = None,
    item_id: str | None = None,
    for_employee_id: str | None = None,
) -> str | Command:
    specs = COURSE.select(facets)
    if item_id is None:
        if not name:
            return reply(runtime, {"error": "укажите name или item_id"})
        try:
            found = unwrap(await runtime.context.mcp.call("item_ids_by_course_names", {"course_name": name})) or []
        except ToolError as exc:
            return reply(runtime, {"error": str(exc)})
        if not found:
            return reply(runtime, {"error": f"курс «{name}» не найден"})
        item_id = next((i for i in found if i.get("name") == name), found[0])["id"]
    guard = any(spec.needs_person for spec in specs)
    return await _run(
        runtime, specs, guard=guard, for_employee_id=for_employee_id, item_id=item_id, keys={"name": name}
    )


@tool("hr_request", description=facet_description(HR_REQUEST))
async def hr_request(runtime: Runtime, facets: list[HrRequestFacet], number: str) -> str | Command:
    return await _run(runtime, HR_REQUEST.select(facets), guard=False, keys={"number": number})


@tool("learning_request", description=facet_description(LEARNING_REQUEST))
async def learning_request(runtime: Runtime, facets: list[LearningRequestFacet], request_id: str) -> str | Command:
    return await _run(runtime, LEARNING_REQUEST.select(facets), guard=False, keys={"request_id": request_id})


@tool("onsite_activity", description=facet_description(ONSITE_ACTIVITY))
async def onsite_activity(runtime: Runtime, facets: list[OnsiteActivityFacet], activity_id: str) -> str | Command:
    return await _run(runtime, ONSITE_ACTIVITY.select(facets), guard=False, keys={"activity_id": activity_id})


@tool("vacancy", description=facet_description(VACANCY))
async def vacancy(
    runtime: Runtime,
    facets: list[VacancyFacet],
    vac_num: int | None = None,
    publication_id: str | None = None,
    job_requisition_id: str | None = None,
    job_application_id: str | None = None,
    position_id: str | None = None,
) -> str | Command:
    keys = {
        "vac_num": vac_num,
        "publication_id": publication_id,
        "job_requisition_id": job_requisition_id,
        "job_application_id": job_application_id,
        "position_id": position_id,
    }
    return await _run(runtime, VACANCY.select(facets), guard=False, keys=keys)


ENTITY_TOOLS = [employee, course, hr_request, learning_request, onsite_activity, vacancy]
