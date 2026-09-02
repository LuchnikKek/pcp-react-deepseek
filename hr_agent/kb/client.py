"""Протокол клиента базы знаний."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from hr_agent.kb.models import Instruction, InstructionHeader


@runtime_checkable
class KbClient(Protocol):
    async def search(self, query: str) -> list[InstructionHeader]:
        """Top-N заголовков по близости запроса к колонке «Вопрос» (N задаёт реализация)."""
        ...

    async def get(self, instruction_id: int) -> Instruction | None: ...
