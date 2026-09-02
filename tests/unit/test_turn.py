import os
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from hr_agent.agent.turn import TurnResult, run_turn
from hr_agent.config import load_dotenv
from hr_agent.facets.mcp import McpClient
from tests.unit.test_agent import CONFIG, GROUP, call, make_agent, reply


async def test_turns_question_then_ticket_offer(mcp: McpClient) -> None:
    script = iter(
        [
            call("ask_user", {"question": "Уточните тематику", "options": ["Стоматология", "Докупной полис"]}, "c1"),
            call("get_instruction", {"id": 48}, "c2"),
            reply("ticket_offer", "Для уточнения нужна заявка", "c3", group=GROUP),
            AIMessage(content="Обычный текст без AgentReply"),
        ]
    )
    agent, _model, ctx = make_agent(script, mcp)
    seen: list[BaseMessage] = []
    first = await run_turn(agent, config=CONFIG, context=ctx, message="гигиена по ДМС", on_message=seen.append)
    assert first == TurnResult("question", "Уточните тематику", options=["Стоматология", "Докупной полис"])
    assert [type(m).__name__ for m in seen] == ["AIMessage"]  # вызов ask_user виден до остановки на interrupt

    seen.clear()
    second = await run_turn(agent, config=CONFIG, context=ctx, message="Докупной полис", on_message=seen.append)
    assert second == TurnResult("ticket_offer", "Для уточнения нужна заявка", group=GROUP)
    tool_results = [m for m in seen if isinstance(m, ToolMessage)]
    assert [m.name for m in tool_results][:2] == ["ask_user", "get_instruction"]
    assert tool_results[0].content == "Докупной полис"

    third = await run_turn(agent, config=CONFIG, context=ctx, message="спасибо")
    assert third == TurnResult("answer", "Обычный текст без AgentReply")


def test_load_dotenv(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text('# comment\nDEEPSEEK_API_KEY="sk-test"\nexport DEEPSEEK_API_BASE=https://x/v1\nBROKEN\n', "utf-8")
    os.environ.pop("DEEPSEEK_API_BASE", None)
    os.environ["DEEPSEEK_API_KEY"] = "already-set"
    try:
        loaded = load_dotenv(env)
        assert loaded == {"DEEPSEEK_API_KEY": "sk-test", "DEEPSEEK_API_BASE": "https://x/v1"}
        assert os.environ["DEEPSEEK_API_KEY"] == "already-set"  # без override не перетирается
        assert os.environ["DEEPSEEK_API_BASE"] == "https://x/v1"
        assert load_dotenv(tmp_path / "missing.env") == {}
    finally:
        os.environ.pop("DEEPSEEK_API_KEY", None)
        os.environ.pop("DEEPSEEK_API_BASE", None)
