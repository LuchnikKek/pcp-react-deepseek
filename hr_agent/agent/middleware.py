"""Middleware агента: динамический системный промпт (§7) и валидатор финального ответа (§10)."""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, dynamic_prompt, hook_config
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.prompt import build_system_prompt
from hr_agent.agent.reply import AgentReply
from hr_agent.agent.state import HrAgentState
from hr_agent.kb.client import KbClient

log = logging.getLogger(__name__)

REPLY_TOOL = AgentReply.__name__  # имя тула, которым ToolStrategy собирает структурированный ответ
REMARK = (
    "Группа заявки «{group}» не встречается в тексте открытых инструкций. "
    "Возьми группу дословно из инструкции или ответь без заявки (kind=answer)."
)


@dynamic_prompt
def system_prompt(request: ModelRequest) -> str:
    ctx: RuntimeContext = request.runtime.context
    state = request.state
    active_id = state.get("active_instruction_id")
    active = (active_id, state.get("active_instruction_question") or "") if active_id is not None else None
    return build_system_prompt(ctx.employee_id, ctx.today, active)


def reply_call(state: HrAgentState) -> dict[str, Any] | None:
    """Вызов AgentReply в последнем сообщении модели (None, если модель звала обычные тулы)."""
    last_ai = next((m for m in reversed(state["messages"]) if isinstance(m, AIMessage)), None)
    if last_ai is None:
        return None
    return next((c for c in last_ai.tool_calls if c["name"] == REPLY_TOOL), None)


async def group_in_instructions(kb: KbClient, ids: list[int], group: str) -> bool:
    for instruction_id in ids:
        instruction = await kb.get(instruction_id)
        if instruction and group.strip() in instruction.text:
            return True
    return False


class ReplyValidator(AgentMiddleware[HrAgentState, RuntimeContext]):
    """ticket_offer.group обязана быть подстрокой текста одной из открытых инструкций.

    Иначе модели возвращается замечание и даётся одна попытка; затем ответ деградирует в answer без заявки.
    """

    state_schema = HrAgentState

    @hook_config(can_jump_to=["model"])
    async def aafter_model(self, state: HrAgentState, runtime: Runtime[RuntimeContext]) -> dict[str, Any] | None:
        call = reply_call(state)
        if call is None:
            return None
        reply = AgentReply.model_validate(call["args"])
        if reply.kind != "ticket_offer":
            return {"reply_retries": 0}
        seen = state.get("seen_instruction_ids") or []
        if reply.group and await group_in_instructions(runtime.context.kb, seen, reply.group):
            return {"reply_retries": 0}
        if state.get("reply_retries", 0) < 1:
            return {
                "messages": [HumanMessage(REMARK.format(group=reply.group))],
                "reply_retries": 1,
                "jump_to": "model",
            }
        log.warning("ticket_offer degraded to answer: group=%r not found in instructions %s", reply.group, seen)
        return {"structured_response": AgentReply(kind="answer", text=reply.text), "reply_retries": 0}
