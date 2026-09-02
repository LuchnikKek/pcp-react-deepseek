"""Обработка одного хода (ARCHITECTURE §6): сообщение или ответ на вопрос агента -> question | answer | ticket_offer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.reply import AgentReply

OnMessage = Callable[[BaseMessage], None]


@dataclass(frozen=True)
class TurnResult:
    kind: Literal["question", "answer", "ticket_offer"]
    text: str
    options: list[str] | None = None  # только для question
    group: str | None = None  # только для ticket_offer


async def run_turn(
    agent: CompiledStateGraph,
    *,
    config: dict[str, Any],
    context: RuntimeContext,
    message: str,
    on_message: OnMessage | None = None,
) -> TurnResult:
    """Если агент ждал ответа на ask_user — возобновляет граф, иначе начинает новый ReAct-цикл.

    on_message — колбэк на каждое новое сообщение по мере хода (reasoning, вызовы тулов, их результаты).
    """
    snapshot = await agent.aget_state(config)
    payload: Any = Command(resume=message) if snapshot.interrupts else {"messages": [HumanMessage(message)]}
    if on_message is None:
        result = await agent.ainvoke(payload, config=config, context=context)
    else:
        result = await _stream(agent, payload, config, context, on_message)

    if interrupts := result.get("__interrupt__"):
        value = interrupts[0].value
        return TurnResult("question", value["question"], options=value.get("options"))
    last_ai = next((m for m in reversed(result["messages"]) if isinstance(m, AIMessage)), None)
    if last_ai is not None and not last_ai.tool_calls:  # модель ответила текстом, минуя AgentReply
        return TurnResult("answer", last_ai.text)
    reply: AgentReply = result["structured_response"]
    return TurnResult(reply.kind, reply.text, group=reply.group)


async def _stream(
    agent: CompiledStateGraph, payload: Any, config: dict[str, Any], context: RuntimeContext, on_message: OnMessage
) -> dict[str, Any]:
    """То же, что ainvoke, но сообщения из обновлений узлов отдаются в on_message сразу."""
    interrupts: Any = None
    async for chunk in agent.astream(payload, config=config, context=context, stream_mode="updates"):
        for node, update in chunk.items():
            if node == "__interrupt__":
                interrupts = update
                continue
            for part in update if isinstance(update, list) else [update]:
                for msg in (part or {}).get("messages") or []:
                    on_message(msg)
    values = dict((await agent.aget_state(config)).values)
    if interrupts:
        values["__interrupt__"] = interrupts
    return values
