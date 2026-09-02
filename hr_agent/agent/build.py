"""Сборка агента: create_agent + тулы + middleware + AgentReply (ARCHITECTURE §3, §9)."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import ClearToolUsesEdit, ContextEditingMiddleware, SummarizationMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.middleware import ReplyValidator, system_prompt
from hr_agent.agent.reply import AgentReply
from hr_agent.agent.state import HrAgentState
from hr_agent.tools import ALL_TOOLS

DEEPSEEK_MODEL = "deepseek-v4-pro-0813:network"
RECURSION_LIMIT = 25  # шагов графа на один ход; задаётся в config вызова
KB_TOOLS = ("search_instructions", "get_instruction", "ask_user")  # их результаты не вычищаются из контекста
CLEAR_TOOL_RESULTS_AFTER_TOKENS = 30_000
SUMMARIZE_AFTER_TOKENS = 60_000
SUMMARY_KEEP_MESSAGES = 20


def make_model(model: str = DEEPSEEK_MODEL, temperature: float = 0.0) -> ChatDeepSeek:
    """DeepSeek через OpenAI-совместимый API; ключ — переменная окружения DEEPSEEK_API_KEY."""
    return ChatDeepSeek(model=model, temperature=temperature)


def build_agent(model: BaseChatModel, checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    return create_agent(
        model=model,
        tools=ALL_TOOLS,
        middleware=[
            system_prompt,
            ReplyValidator(),
            ContextEditingMiddleware(
                edits=[ClearToolUsesEdit(trigger=CLEAR_TOOL_RESULTS_AFTER_TOKENS, keep=3, exclude_tools=list(KB_TOOLS))]
            ),
            SummarizationMiddleware(
                model, trigger=("tokens", SUMMARIZE_AFTER_TOKENS), keep=("messages", SUMMARY_KEEP_MESSAGES)
            ),
        ],
        response_format=ToolStrategy(AgentReply),
        state_schema=HrAgentState,
        context_schema=RuntimeContext,
        checkpointer=checkpointer,
    )
