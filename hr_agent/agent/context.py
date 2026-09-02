"""Runtime context одного вызова агента (ARCHITECTURE §6, п. 2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hr_agent.facets.mcp import McpCaller
from hr_agent.kb.client import KbClient


@dataclass
class RuntimeContext:
    employee_id: str
    session_id: str
    today: date
    mcp: McpCaller
    kb: KbClient
    person_id: str | None = None
