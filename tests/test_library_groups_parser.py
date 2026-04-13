from bot.services.keywords import detect_keywords
from bot.services.parser import parse_link_input


def test_parse_link_extracts_keywords_and_category():
    parsed = parse_link_input(
        "https://example.com/agent #Skill #Plan @ai-agent ghi chu quan trong"
    )

    assert parsed["url"] == "https://example.com/agent"
    assert set(parsed["tags"]) == {"Skill", "Plan"}
    assert parsed["category"] == "AI Agent"
    assert parsed["notes"] == "ghi chu quan trong"


def test_parse_link_ignores_legacy_priority_marker():
    parsed = parse_link_input("https://example.com/docs !high #react")

    assert parsed["url"] == "https://example.com/docs"
    assert set(parsed["tags"]) == {"react"}
    assert parsed["notes"] == ""


def test_detect_keywords_for_ai_agent_includes_skill_plan():
    keywords = detect_keywords(
        url="https://example.com/ai-agent-skill-plan",
        title="AI Agent skill plan",
        summary="plan-and-execute",
        topic="AI Agent",
        manual_keywords=["custom"],
    )

    assert "ai-agent" in keywords
    assert "skill" in keywords
    assert "plan" in keywords
    assert "custom" in keywords
