"""In-memory база знаний для тестов: счёт — доля слов запроса, найденных в вопросе."""

from __future__ import annotations

from collections.abc import Iterable

from hr_agent.kb.models import Instruction, InstructionHeader


class InMemoryKb:
    def __init__(self, instructions: Iterable[Instruction], top_n: int = 10) -> None:
        self._items = {i.id: i for i in instructions}
        self._top_n = top_n

    async def search(self, query: str) -> list[InstructionHeader]:
        words = query.lower().split()
        scored: list[tuple[float, Instruction]] = []
        for item in self._items.values():
            hits = sum(w in item.question.lower() for w in words)
            if hits:
                scored.append((hits / len(words), item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].id))
        return [item.header(score) for score, item in scored[: self._top_n]]

    async def get(self, instruction_id: int) -> Instruction | None:
        return self._items.get(instruction_id)
