from bot.services.category import (
    detect_category,
    is_forbidden_other_category,
    normalize_category_name,
)
from bot.services.parser import parse_link_input


def test_parse_link_without_category_keeps_category_empty():
    parsed = parse_link_input("https://example.com/react-guide #ui")
    assert parsed["category"] == ""


def test_parse_link_normalizes_marketing_typo_alias():
    parsed = parse_link_input("https://example.com/growth @maketing")
    assert parsed["category"] == "Marketing"


def test_parse_link_normalizes_uiux_alias():
    parsed = parse_link_input("https://example.com/figma @uiux")
    assert parsed["category"] == "UIUX"


def test_detect_category_prefers_domain_rules():
    category = detect_category("https://www.figma.com/file/123", "Design file")
    assert category == "UIUX"


def test_detect_category_by_frontend_keywords():
    category = detect_category(
        "https://example.com/blog/frontend",
        title="React component patterns",
        summary="Build reusable components with Tailwind and TypeScript.",
    )
    assert category == "FE"


def test_detect_category_fallback_never_returns_other():
    category = detect_category("https://example.com/unknown", "General note")
    assert category == "Tech"


def test_other_category_is_forbidden_and_not_normalized():
    assert normalize_category_name("Other") == ""
    assert is_forbidden_other_category("other")
