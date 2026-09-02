from langchain_core.utils.function_calling import convert_to_openai_tool

from hr_agent.facets.identity import ACCESS_DENIED
from hr_agent.facets.mcp import McpClient
from hr_agent.facets.registry import EMPLOYEE
from hr_agent.tools import ALL_TOOLS, course, employee, hr_request, learning_request, vacancy
from tests.conftest import (
    COURSE_ID,
    COURSE_NAME,
    EMPLOYEE_ID,
    EMPTY_EMPLOYEE_ID,
    PERSON_ID,
    STRANGER_ID,
    SUBORDINATE_ID,
    ToolRunner,
    last_json,
    make_context,
)


def test_nine_tools_with_names_from_architecture() -> None:
    assert [t.name for t in ALL_TOOLS] == [
        "search_instructions",
        "get_instruction",
        "ask_user",
        "employee",
        "course",
        "hr_request",
        "learning_request",
        "onsite_activity",
        "vacancy",
    ]


def test_employee_schema_built_from_registry() -> None:
    params = convert_to_openai_tool(employee)["function"]["parameters"]
    assert "runtime" not in params["properties"]
    assert params["properties"]["facets"]["items"]["enum"] == list(EMPLOYEE.names())
    assert params["required"] == ["facets"]
    for facet in EMPLOYEE.facets:
        assert f"- {facet.name}: {facet.description}" in employee.description


async def test_employee_own_facets_and_identity_in_state(mcp: McpClient) -> None:
    runner = ToolRunner(employee, make_context(mcp))
    result = await runner.invoke({"facets": ["basic", "position", "insurance", "absence_limits"]})
    payload = last_json(result)
    assert set(payload) == {"basic", "position", "insurance", "absence_limits"}
    assert payload["basic"]["hireDate"] == "2018-07-02"
    assert payload["basic"]["lengthOfServiceYears"] == "4"
    assert "personId" not in payload["basic"]
    assert payload["position"][0]["gradeLevel"] == 15
    assert payload["insurance"]["insurance"] == {}
    assert payload["absence_limits"][0]["DateReqBeg"] == "2026-01-01"
    assert result["identity"] == {"employee_id": EMPLOYEE_ID, "person_id": PERSON_ID, "subordinates": None}


async def test_employee_empty_collection_is_empty_list(mcp: McpClient) -> None:
    runner = ToolRunner(employee, make_context(mcp, employee_id=EMPTY_EMPLOYEE_ID))
    assert last_json(await runner.invoke({"facets": ["events", "sicklists"]})) == {"events": [], "sicklists": []}


async def test_employee_org_chain_and_people(mcp: McpClient) -> None:
    runner = ToolRunner(employee, make_context(mcp))
    payload = last_json(await runner.invoke({"facets": ["org_chain", "subordinates", "hrbp", "contacts"]}))
    chain = payload["org_chain"]
    assert len(chain) >= 2 and chain[-1]["type"] == "POSITION"
    assert any(p["employeeId"] == SUBORDINATE_ID for p in payload["subordinates"])
    assert all(set(p) == {"fullName", "employeeId", "position", "kostlName"} for p in payload["hrbp"])
    assert payload["contacts"]["J.CONTACTS.EXTERNALEMAIL"]


async def test_employee_stranger_denied_but_identity_kept(mcp: McpClient) -> None:
    runner = ToolRunner(employee, make_context(mcp))
    result = await runner.invoke({"facets": ["basic"], "for_employee_id": STRANGER_ID})
    assert last_json(result) == {"error": ACCESS_DENIED}
    assert SUBORDINATE_ID in result["identity"]["subordinates"]


async def test_employee_subordinate_passes_guard(mcp: McpClient) -> None:
    runner = ToolRunner(employee, make_context(mcp))
    payload = last_json(await runner.invoke({"facets": ["basic"], "for_employee_id": SUBORDINATE_ID}))
    assert "не найден" in payload["basic"]["error"]  # мок не знает профиль подчинённого


async def test_employee_unknown_facet_rejected(mcp: McpClient) -> None:
    runner = ToolRunner(employee, make_context(mcp))
    message = (await runner.invoke({"facets": ["salary"]}))["messages"][-1]
    assert message.status == "error"


async def test_course_by_name(mcp: McpClient) -> None:
    runner = ToolRunner(course, make_context(mcp))
    payload = last_json(await runner.invoke({"facets": ["catalog", "tags", "availability"], "name": COURSE_NAME}))
    assert payload["catalog"][0]["id"] == COURSE_ID
    assert set(payload["catalog"][0]) <= {"id", "name", "type", "status", "description", "duration"}
    assert payload["tags"] == []
    assert payload["availability"] == []


async def test_course_errors(mcp: McpClient) -> None:
    runner = ToolRunner(course, make_context(mcp))
    assert last_json(await runner.invoke({"facets": ["tags"], "name": "нет такого курса"})) == {
        "error": "курс «нет такого курса» не найден"
    }
    assert last_json(await runner.invoke({"facets": ["tags"]})) == {"error": "укажите name или item_id"}
    payload = last_json(await runner.invoke({"facets": ["catalog"], "item_id": COURSE_ID}))
    assert payload == {"catalog": {"error": "не указан name"}}


async def test_keyed_entities_without_guard(mcp: McpClient) -> None:
    payload = last_json(await ToolRunner(hr_request, make_context(mcp)).invoke({"facets": ["status"], "number": "1"}))
    assert "не найдена" in payload["status"]["error"]

    runner = ToolRunner(learning_request, make_context(mcp))
    payload = last_json(await runner.invoke({"facets": ["info"], "request_id": "no-such"}))
    assert "не найдена" in payload["info"]["error"]


async def test_vacancy_keys(mcp: McpClient) -> None:
    runner = ToolRunner(vacancy, make_context(mcp))
    payload = last_json(await runner.invoke({"facets": ["job", "publications"], "job_requisition_id": "x"}))
    assert payload == {"job": {"error": "не указан vac_num"}, "publications": []}
