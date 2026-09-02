"""Сборка агента на скриптованной модели: промпт, валидатор group, interrupt, деградация."""

from collections.abc import Iterator
from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from hr_agent.agent.build import RECURSION_LIMIT, build_agent
from hr_agent.agent.middleware import REMARK
from hr_agent.facets.mcp import McpClient
from tests.conftest import make_context

GROUP = "ДМС Мое здоровье_МИП - экспертиза дмс"
CONFIG = {"configurable": {"thread_id": "t1"}, "recursion_limit": RECURSION_LIMIT}


class ScriptedModel(GenericFakeChatModel):
    """Отдаёт заранее заданные ответы и запоминает системные промпты, которые получала."""

    prompts: list[str] = []

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedModel":
        return self

    def _generate(self, messages: list, *args: Any, **kwargs: Any) -> ChatResult:
        if messages and isinstance(messages[0], SystemMessage):
            self.prompts.append(str(messages[0].content))
        return super()._generate(messages, *args, **kwargs)


def call(name: str, args: dict[str, Any], call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def reply(kind: str, text: str, call_id: str, group: str | None = None) -> AIMessage:
    return call("AgentReply", {"kind": kind, "text": text, "group": group}, call_id)


def make_agent(script: Iterator[AIMessage], mcp: McpClient) -> tuple[Any, ScriptedModel, Any]:
    model = ScriptedModel(messages=script, prompts=[])
    return build_agent(model, checkpointer=InMemorySaver()), model, make_context(mcp)


async def test_bad_group_gets_one_retry(mcp: McpClient) -> None:
    script = iter(
        [
            call("get_instruction", {"id": 48}, "c1"),
            reply("ticket_offer", "Нужна заявка", "c2", group="Неправильная группа"),
            reply("ticket_offer", "Нужна заявка", "c3", group=GROUP),
        ]
    )
    agent, model, ctx = make_agent(script, mcp)
    result = await agent.ainvoke({"messages": [HumanMessage("докупной полис")]}, config=CONFIG, context=ctx)
    assert result["structured_response"].model_dump() == {
        "kind": "ticket_offer",
        "text": "Нужна заявка",
        "group": GROUP,
    }
    assert any(
        isinstance(m, HumanMessage) and m.content == REMARK.format(group="Неправильная группа")
        for m in result["messages"]
    )
    assert result["reply_retries"] == 0
    assert "Активная инструкция №48: «Входит ли гигиена в стоматологию по ДМС?»" in model.prompts[-1]
    assert "Активная инструкция" not in model.prompts[0]


async def test_second_bad_group_degrades_to_answer(mcp: McpClient) -> None:
    script = iter(
        [
            call("get_instruction", {"id": 48}, "c1"),
            reply("ticket_offer", "Нужна заявка", "c2", group="Группа 1"),
            reply("ticket_offer", "Нужна заявка", "c3", group="Группа 2"),
        ]
    )
    agent, _model, ctx = make_agent(script, mcp)
    result = await agent.ainvoke({"messages": [HumanMessage("докупной полис")]}, config=CONFIG, context=ctx)
    assert result["structured_response"].model_dump() == {"kind": "answer", "text": "Нужна заявка", "group": None}


async def test_answer_passes_without_remark(mcp: McpClient) -> None:
    agent, _model, ctx = make_agent(iter([reply("answer", "Ответ по инструкции", "c1")]), mcp)
    result = await agent.ainvoke({"messages": [HumanMessage("вопрос")]}, config=CONFIG, context=ctx)
    assert result["structured_response"].kind == "answer"
    assert not any(isinstance(m, HumanMessage) and "Группа заявки" in str(m.content) for m in result["messages"])


async def test_ask_user_interrupts_and_resumes(mcp: McpClient) -> None:
    script = iter(
        [
            call("ask_user", {"question": "Уточните тематику", "options": ["Стоматология", "Докупной полис"]}, "c1"),
            reply("answer", "Ответ после уточнения", "c2"),
        ]
    )
    agent, _model, ctx = make_agent(script, mcp)
    paused = await agent.ainvoke({"messages": [HumanMessage("гигиена по ДМС")]}, config=CONFIG, context=ctx)
    assert paused["__interrupt__"][0].value == {
        "question": "Уточните тематику",
        "options": ["Стоматология", "Докупной полис"],
    }
    assert paused.get("structured_response") is None  # ход ещё не завершён: исход только через __interrupt__

    resumed = await agent.ainvoke(Command(resume="Докупной полис"), config=CONFIG, context=ctx)
    assert resumed["structured_response"].text == "Ответ после уточнения"
