"""Девять тулов агента (ARCHITECTURE §5)."""

from langchain_core.tools import BaseTool

from hr_agent.tools.ask_user import ask_user
from hr_agent.tools.entities import (
    ENTITY_TOOLS,
    course,
    employee,
    hr_request,
    learning_request,
    onsite_activity,
    vacancy,
)
from hr_agent.tools.kb import get_instruction, search_instructions

ALL_TOOLS: list[BaseTool] = [search_instructions, get_instruction, ask_user, *ENTITY_TOOLS]

__all__ = [
    "ALL_TOOLS",
    "ask_user",
    "course",
    "employee",
    "get_instruction",
    "hr_request",
    "learning_request",
    "onsite_activity",
    "search_instructions",
    "vacancy",
]
