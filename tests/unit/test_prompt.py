from datetime import date

from hr_agent.agent.prompt import GLOSSARY, build_system_prompt


def test_prompt_without_active_instruction() -> None:
    prompt = build_system_prompt("1655480", date(2026, 9, 2))
    assert "Сегодня 2026-09-02" in prompt
    assert "Табельный номер пользователя: 1655480" in prompt
    assert "Активная инструкция" not in prompt
    for phrase, facet in GLOSSARY:
        assert f"- {phrase} → {facet}" in prompt
    assert "ticket_offer" in prompt and "ask_user" in prompt


def test_prompt_with_active_instruction() -> None:
    prompt = build_system_prompt("1655480", date(2026, 9, 2), (48, "Входит ли гигиена?"))
    assert "Активная инструкция №48: «Входит ли гигиена?»" in prompt
    assert "get_instruction(48)" in prompt
