"""Финальный ответ агента (ARCHITECTURE §5.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentReply(BaseModel):
    """Финальный ответ сотруднику: текстовый ответ либо предложение создать заявку."""

    kind: Literal["answer", "ticket_offer"] = Field(
        description="answer — текстовый ответ; ticket_offer — предложить сотруднику создать заявку"
    )
    text: str = Field(description="Текст для сотрудника; для ticket_offer — сопроводительное сообщение из инструкции")
    group: str | None = Field(
        default=None, description="Группа заявки дословно из текста инструкции; обязательна для ticket_offer"
    )
