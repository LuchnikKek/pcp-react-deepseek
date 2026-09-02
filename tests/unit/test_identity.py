import pytest

from hr_agent.facets.identity import AccessDenied, Identity, ensure_identity, pick_target
from hr_agent.facets.mcp import McpClient
from tests.conftest import EMPLOYEE_ID, PERSON_ID, STRANGER_ID, SUBORDINATE_ID, CountingMcp


async def test_ensure_identity_resolves_once_and_caches(mcp: McpClient) -> None:
    counting = CountingMcp(mcp)
    identity = await ensure_identity(
        counting, employee_id="01655480", person_id=None, identity=None, need_subordinates=False
    )
    assert identity == {"employee_id": EMPLOYEE_ID, "person_id": PERSON_ID, "subordinates": None}
    assert counting.calls == ["get_id_mapper_person_id"]

    counting.calls.clear()
    with_subs = await ensure_identity(
        counting, employee_id=EMPLOYEE_ID, person_id=None, identity=identity, need_subordinates=True
    )
    assert counting.calls == ["org_structure_subordinate"]
    assert SUBORDINATE_ID in with_subs["subordinates"]

    counting.calls.clear()
    again = await ensure_identity(
        counting, employee_id=EMPLOYEE_ID, person_id=None, identity=with_subs, need_subordinates=True
    )
    assert again == with_subs and counting.calls == []


async def test_provided_person_id_skips_id_mapper(mcp: McpClient) -> None:
    counting = CountingMcp(mcp)
    identity = await ensure_identity(
        counting, employee_id=EMPLOYEE_ID, person_id=PERSON_ID, identity=None, need_subordinates=False
    )
    assert identity["person_id"] == PERSON_ID and counting.calls == []


async def test_identity_of_another_user_is_replaced(mcp: McpClient) -> None:
    stale = Identity(employee_id=STRANGER_ID, person_id="x", subordinates={})
    identity = await ensure_identity(
        mcp, employee_id=EMPLOYEE_ID, person_id=None, identity=stale, need_subordinates=False
    )
    assert identity["employee_id"] == EMPLOYEE_ID and identity["person_id"] == PERSON_ID


def test_pick_target() -> None:
    identity = Identity(employee_id=EMPLOYEE_ID, person_id=PERSON_ID, subordinates={SUBORDINATE_ID: "sub-person"})
    assert pick_target(identity, None) == (EMPLOYEE_ID, PERSON_ID)
    assert pick_target(identity, "01655480") == (EMPLOYEE_ID, PERSON_ID)
    assert pick_target(identity, SUBORDINATE_ID) == (SUBORDINATE_ID, "sub-person")
    with pytest.raises(AccessDenied):
        pick_target(identity, STRANGER_ID)
    with pytest.raises(AccessDenied):
        pick_target(Identity(employee_id=EMPLOYEE_ID, person_id=PERSON_ID, subordinates=None), SUBORDINATE_ID)
