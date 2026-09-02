"""Модели базы знаний."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

InstructionType = Literal["RAG", "API", "API_HARD"]

STATUS_FALSE = "status_false"  # инструкции для операторов 1-й линии, модели не показываются


class InstructionHeader(BaseModel):
    id: int
    question: str
    type: InstructionType
    topics: list[str]
    score: float
    status: str


class Instruction(BaseModel):
    id: int
    question: str
    type: InstructionType
    topics: list[str]
    text: str
    status: str

    def header(self, score: float) -> InstructionHeader:
        return InstructionHeader(
            id=self.id,
            question=self.question,
            type=self.type,
            topics=self.topics,
            score=score,
            status=self.status,
        )
