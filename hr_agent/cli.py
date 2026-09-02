"""Интерактивный чат с агентом для проверки интеграции: DeepSeek + моковый MCP in-process + БЗ из xlsx.

uv run python -m hr_agent.cli --employee 1655480
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import date

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from hr_agent.agent.build import DEEPSEEK_MODEL, RECURSION_LIMIT, build_agent, make_model
from hr_agent.agent.context import RuntimeContext
from hr_agent.agent.turn import TurnResult, run_turn
from hr_agent.config import load_dotenv
from hr_agent.facets.mcp import McpClient
from hr_agent.kb.xlsx import XlsxKb
from mock_mcp_server.server import build_app

EXIT_WORDS = {"exit", "quit", "выход"}
REASONING_LIMIT = 2000
RESULT_LIMIT = 400


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Чат с HR-агентом (моковые HR-сервисы, БЗ из xlsx)")
    parser.add_argument("--employee", default="1655480", help="табельный номер пользователя (по умолчанию 1655480)")
    parser.add_argument("--person-id", default=None, help="person_id пользователя, если известен")
    parser.add_argument("--xlsx", default="bz_cut.xlsx", help="срез базы знаний")
    parser.add_argument("--model", default=DEEPSEEK_MODEL, help="модель DeepSeek")
    parser.add_argument("--env", default=".env", help="файл с DEEPSEEK_API_KEY / DEEPSEEK_API_BASE")
    parser.add_argument("--quiet", action="store_true", help="не печатать reasoning и вызовы тулов")
    return parser.parse_args(argv)


def trim(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else f"{text[:limit]}… [ещё {len(text) - limit} символов]"


def print_message(message: BaseMessage) -> None:
    """Трассировка хода: reasoning модели, промежуточный текст, вызовы тулов, результаты, замечания валидатора."""
    if isinstance(message, AIMessage):
        if reasoning := message.additional_kwargs.get("reasoning_content"):
            print(f"  [reasoning] {trim(str(reasoning), REASONING_LIMIT)}")
        if message.text and message.tool_calls:
            print(f"  [текст] {trim(message.text, RESULT_LIMIT)}")
        for call in message.tool_calls:
            print(f"  [tool_call] {call['name']}({json.dumps(call['args'], ensure_ascii=False)})")
    elif isinstance(message, ToolMessage):
        print(f"  [tool_result] {message.name}: {trim(str(message.content), RESULT_LIMIT)}")
    elif isinstance(message, HumanMessage):
        print(f"  [validator] {message.text}")


def print_result(result: TurnResult) -> None:
    if result.kind == "question":
        print(f"агент? {result.text}")
        for i, option in enumerate(result.options or [], 1):
            print(f"   {i}. {option}")
    elif result.kind == "ticket_offer":
        print(f"агент: {result.text}\n   [заявка на группу: {result.group}]")
    else:
        print(f"агент: {result.text}")


async def chat(args: argparse.Namespace) -> None:
    load_dotenv(args.env)
    session_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": RECURSION_LIMIT}
    async with McpClient(build_app(), timeout=10) as mcp:
        context = RuntimeContext(
            employee_id=args.employee,
            session_id=session_id,
            today=date.today(),
            mcp=mcp,
            kb=XlsxKb(args.xlsx),
            person_id=args.person_id,
        )
        agent = build_agent(make_model(args.model), checkpointer=InMemorySaver())
        print(f"Сессия {session_id[:8]}, сотрудник {args.employee}, модель {args.model}. Выход: exit.")
        while True:
            try:
                message = (await asyncio.to_thread(input, "вы> ")).strip()
            except EOFError:
                break
            if not message or message.lower() in EXIT_WORDS:
                break
            try:
                result = await run_turn(
                    agent,
                    config=config,
                    context=context,
                    message=message,
                    on_message=None if args.quiet else print_message,
                )
            except Exception as exc:  # noqa: BLE001 — в чате показываем любую ошибку, не падаем
                print(f"ошибка: {type(exc).__name__}: {exc}")
                continue
            print_result(result)


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(chat(parse_args(argv)))


if __name__ == "__main__":
    main()
