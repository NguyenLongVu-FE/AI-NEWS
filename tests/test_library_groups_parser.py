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


def test_detect_keywords_extracts_technical_terms_from_summary():
    keywords = detect_keywords(
        url="https://example.com/post",
        title="Workflow guide",
        summary="Huong dan xay dung AI agent workflow voi LangGraph va prompt template.",
        topic="AI Agent",
        manual_keywords=[],
    )

    assert "langgraph" in keywords
    assert "prompt-template" in keywords
    assert "agent-workflow" in keywords


def test_detect_keywords_summary_merge_deduplicates_with_manual_input():
    keywords = detect_keywords(
        url="https://example.com/automation",
        title="Automation",
        summary="AI agent plan va skill planning",
        topic="AI Agent",
        manual_keywords=["plan", "skill", "custom"],
    )

    assert keywords.count("plan") == 1
    assert keywords.count("skill") == 1
    assert "custom" in keywords


def test_detect_keywords_always_has_topic_keyword_for_generic_content():
    keywords = detect_keywords(
        url="https://example.com/business-update",
        title="Ban tin doanh nghiep",
        summary="Thong tin cap nhat quy 2 cho doanh nghiep va thi truong",
        topic="Business",
        manual_keywords=[],
    )

    assert "business" in keywords
    assert len(keywords) >= 1
    assert "doanh" in keywords


def test_detect_keywords_ignores_no_summary_placeholder_noise():
    keywords = detect_keywords(
        url="https://example.com/empty-summary",
        title="Cap nhat nhanh",
        summary="Chưa có tóm tắt",
        topic="Tech",
        manual_keywords=[],
    )

    assert "tech" in keywords
    assert "chua" not in keywords
