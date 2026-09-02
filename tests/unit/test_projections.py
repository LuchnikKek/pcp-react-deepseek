import pytest

from hr_agent.facets import projections as pj
from hr_agent.facets.mcp import McpClient
from tests.conftest import EMPLOYEE_ID, PERSON_ID


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2025-12-10T14:03:53.819794Z", "2025-12-10"),
        ("2023-12-15T05:23:03.244721+03:00", "2023-12-15"),
        ("2021-11-02T13:00:36.124097", "2021-11-02"),
        ("20260822", "2026-08-22"),
        ("2020-01-01", "2020-01-01"),
        ("00:00", "00:00"),
        (None, None),
    ],
)
def test_norm_date(value: object, expected: object) -> None:
    assert pj.norm_date(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("01655480", "1655480"), ("1655480", "1655480"), ("00000000", "0"), ("", None), (None, None), (4441, "4441")],
)
def test_strip_leading_zeros(value: object, expected: str | None) -> None:
    assert pj.strip_leading_zeros(value) == expected


def test_unwrap() -> None:
    assert pj.unwrap({"d": {"results": [1]}}) == [1]
    assert pj.unwrap({"d": {"Chief": False}}) == {"Chief": False}
    assert pj.unwrap({"success": True, "data": [{"id": 1}]}) == [{"id": 1}]
    assert pj.unwrap({"insurance": {}}) == {"insurance": {}}
    assert pj.unwrap([{"response": []}]) == [{"response": []}]


def test_clean() -> None:
    row = {
        "__metadata": {"id": "x"},
        "success": True,
        "Pernr": "00004441",
        "DateReqBeg": "20260101",
        "LimId": "00000020",
        "created": "2025-01-02T10:00:00Z",
        "nested": [{"meta": {}, "personId": "00106717", "validTo": "9999-12-31"}],
    }
    assert pj.clean(row) == {
        "Pernr": "4441",
        "DateReqBeg": "2026-01-01",
        "LimId": "00000020",
        "created": "2025-01-02",
        "nested": [{"personId": "00106717", "validTo": "9999-12-31"}],
    }


def test_pick() -> None:
    assert pj.pick({"a": 1, "b": 2}, ("a", "c")) == {"a": 1}
    assert pj.pick([{"a": 1, "b": 2}], ("b",)) == [{"b": 2}]
    assert pj.pick({"a": 1}, ()) == {"a": 1}
    assert pj.pick(None, ("a",)) is None


def test_segment() -> None:
    raw = {"data": [{"type": "J.BASIC", "data": {"hireDate": "2018-07-02"}}]}
    assert pj.segment(raw, "J.BASIC") == {"hireDate": "2018-07-02"}
    assert pj.segment(raw, "J.POSITION") is None


def test_org_chain_flattens_children() -> None:
    vertices = [{"name": "Банк", "type": "DEPARTMENT", "children": [{"name": "Отдел", "type": "DEPARTMENT"}]}]
    assert pj.org_chain({"name": "Эксперт", "type": "POSITION"}, vertices) == [
        {"name": "Банк", "type": "DEPARTMENT"},
        {"name": "Отдел", "type": "DEPARTMENT"},
        {"name": "Эксперт", "type": "POSITION"},
    ]


def test_people_walks_top_level_and_children() -> None:
    raw = {
        "data": [
            {
                "name": "Начальник",
                "personEdges": [
                    {
                        "person": {"lastName": "Иванов", "firstName": "Иван", "midName": None},
                        "data": {"employeeId": "0012", "kostlName": "Отдел"},
                    }
                ],
                "children": [
                    {
                        "name": "Эксперт",
                        "personEdges": [
                            {"person": {"lastName": "Петров", "firstName": "Пётр"}, "data": {"employeeId": "34"}}
                        ],
                    }
                ],
            }
        ]
    }
    assert pj.people(raw) == [
        {"fullName": "Иванов Иван", "employeeId": "12", "position": "Начальник", "kostlName": "Отдел"},
        {"fullName": "Петров Пётр", "employeeId": "34", "position": "Эксперт", "kostlName": None},
    ]


async def test_projections_on_real_mock_bodies(mcp: McpClient) -> None:
    profile = await mcp.call("person_profile", {"employee_id": EMPLOYEE_ID, "segments_raw": "J.BASIC"})
    assert pj.segment(profile, "J.BASIC")["hireDate"] == "2018-07-02"
    insurance = pj.clean(pj.unwrap(await mcp.call("get_health_company_name", {"person_id": PERSON_ID})))
    assert insurance["insurance"] == {} and insurance["city"] == "Москва"
    limits = pj.clean(pj.unwrap(await mcp.call("absence_limit", {"employee_id": EMPLOYEE_ID})))
    assert limits and all(lim["Pernr"] == EMPLOYEE_ID and lim["DateReqBeg"].count("-") == 2 for lim in limits)
    assert all("__metadata" not in lim for lim in limits)
