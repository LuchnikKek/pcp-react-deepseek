from hr_agent.facets.mcp import McpClient
from hr_agent.tools import ask_user
from tests.conftest import ToolRunner, make_context


async def test_ask_user_interrupts_and_returns_answer(mcp: McpClient) -> None:
    runner = ToolRunner(ask_user, make_context(mcp))
    result = await runner.invoke(
        {"question": "Уточните тематику", "options": ["Стоматология от Сбера", "Докупной полис"]}
    )
    assert result["__interrupt__"][0].value == {
        "question": "Уточните тематику",
        "options": ["Стоматология от Сбера", "Докупной полис"],
    }

    resumed = await runner.resume("Докупной полис")
    assert "__interrupt__" not in resumed
    assert resumed["messages"][-1].content == "Докупной полис"
