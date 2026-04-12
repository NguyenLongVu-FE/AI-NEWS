from bot.services.library_groups import detect_library_group, normalize_library_group
from bot.services.parser import parse_link_input


def test_parse_link_extracts_library_group_override():
    parsed = parse_link_input("https://ui.shadcn.com/docs/components/button ~shadcn")
    assert parsed["library_group_override"] == "shadcn"


def test_parse_link_invalid_library_group_override_returns_empty():
    parsed = parse_link_input("https://example.com/docs ~not-a-real-group")
    assert parsed["library_group_override"] == ""


def test_parse_link_existing_fields_are_preserved():
    parsed = parse_link_input("https://example.com #ui !high @Tech useful note")

    assert parsed["url"] == "https://example.com"
    assert set(parsed["tags"]) == {"ui"}
    assert parsed["priority"] == "high"
    assert parsed["category"] == "Tech"
    assert parsed["notes"] == "useful note"


def test_parse_link_ignores_tilde_group_inside_url_path():
    parsed = parse_link_input("https://example.com/docs/~shadcn/button")
    assert parsed["library_group_override"] == ""


def test_detect_library_group_from_motion_domain():
    group = detect_library_group("https://motion.dev/docs", "Motion docs", "")
    assert group == "animation"


def test_detect_library_group_ignores_domain_rules_in_title_text():
    group = detect_library_group("https://example.com/docs", "Compare with motion.dev docs", "")
    assert group == "utils"


def test_detect_library_group_tanstack_query_is_not_table():
    group = detect_library_group("https://tanstack.com/query", "TanStack Query docs", "")
    assert group == "utils"


def test_normalize_library_group_unknown_returns_none():
    assert normalize_library_group("something-random") is None
