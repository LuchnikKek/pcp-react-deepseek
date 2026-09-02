"""Состояние thread'а агента (ARCHITECTURE §9)."""

from __future__ import annotations

from typing import Annotated, NotRequired

from langchain.agents import AgentState

from hr_agent.facets.identity import Identity


def add_unique(left: list[int], right: list[int]) -> list[int]:
    out = list(left)
    for item in right:
        if item not in out:
            out.append(item)
    return out


class HrAgentState(AgentState):
    active_instruction_id: NotRequired[int | None]
    seen_instruction_ids: NotRequired[Annotated[list[int], add_unique]]
    identity: NotRequired[Identity | None]
