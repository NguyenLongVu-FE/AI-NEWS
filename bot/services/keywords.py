import re
import unicodedata
from typing import Iterable, Optional


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_TEXT_RE = re.compile(r"[^a-z0-9]+")
_MAX_KEYWORDS = 3

_NO_SUMMARY_MARKERS = {
    "chua co tom tat",
    "no summary",
    "no summary yet",
}

_GLOBAL_SIGNAL_RULES = (
    ("skill", "skill"),
    ("plan", "plan"),
    ("plan and execute", "plan"),
    ("tool calling", "tool-calling"),
    ("workflow", "workflow"),
    ("edit", "edit"),
    ("figma", "figma"),
    ("wireframe", "wireframe"),
    ("prototype", "prototype"),
    ("user flow", "user-flow"),
    ("usability", "usability"),
    ("ui ux", "ui-ux"),
    ("ux ui", "ui-ux"),
    ("user experience", "ui-ux"),
    ("react", "react"),
    ("nextjs", "nextjs"),
    ("next js", "nextjs"),
    ("tailwind", "tailwind"),
    ("typescript", "typescript"),
    ("javascript", "javascript"),
    ("css", "css"),
    ("html", "html"),
    ("shadcn", "shadcn"),
    ("python", "python"),
    ("api", "api"),
)

_TOPIC_SIGNAL_RULES = {
    "ai-agent": (
        ("ai agent", "ai-agent"),
        ("agentic", "agentic"),
        ("skill", "skill"),
        ("plan", "plan"),
        ("langgraph", "langgraph"),
        ("crewai", "crewai"),
        ("autogen", "autogen"),
    ),
    "uiux": (
        ("ui ux", "ui-ux"),
        ("ux ui", "ui-ux"),
        ("wireframe", "wireframe"),
        ("prototype", "prototype"),
        ("user flow", "user-flow"),
        ("design system", "design-system"),
        ("accessibility", "accessibility"),
    ),
    "fe": (
        ("react", "react"),
        ("nextjs", "nextjs"),
        ("next js", "nextjs"),
        ("tailwind", "tailwind"),
        ("typescript", "typescript"),
        ("javascript", "javascript"),
        ("css", "css"),
        ("html", "html"),
    ),
}

_TOPIC_FALLBACK_KEYWORD = {
    "ai-agent": "ai-agent",
    "uiux": "ui-ux",
    "fe": "frontend",
    "design": "design",
    "marketing": "marketing",
    "business": "business",
    "education": "education",
    "health": "health",
    "entertainment": "entertainment",
    "tech": "tech",
}


def _normalize_text(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return _TEXT_RE.sub(" ", ascii_text).strip()


def _contains_phrase(content: str, phrase: str) -> bool:
    needle = _normalize_text(phrase)
    if not needle:
        return False
    return f" {needle} " in f" {content} "


def normalize_keyword(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return _SLUG_RE.sub("-", ascii_text).strip("-")


def normalize_keywords(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen = set()
    for value in values:
        token = normalize_keyword(value)
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _detect_rule_keywords(content: str, topic_slug: str) -> list[str]:
    detected: list[str] = []
    for phrase, keyword in _GLOBAL_SIGNAL_RULES:
        if _contains_phrase(content, phrase):
            detected.append(keyword)
    for phrase, keyword in _TOPIC_SIGNAL_RULES.get(topic_slug, ()):
        if _contains_phrase(content, phrase):
            detected.append(keyword)
    return detected


def detect_keywords(
    url: str,
    title: str = "",
    summary: str = "",
    topic: str = "",
    manual_keywords: Optional[Iterable[str]] = None,
) -> list[str]:
    topic_slug = normalize_keyword(topic)
    normalized_summary = _normalize_text(summary)
    summary_missing = normalized_summary in _NO_SUMMARY_MARKERS

    parts = [url, title]
    if not summary_missing:
        parts.append(summary)
    content = _normalize_text(" ".join(str(part or "") for part in parts))

    detected: list[str] = []
    if manual_keywords:
        detected.extend(str(keyword) for keyword in manual_keywords)
    detected.extend(_detect_rule_keywords(content, topic_slug))

    normalized = normalize_keywords(detected)
    if normalized:
        return normalized[:_MAX_KEYWORDS]

    fallback = _TOPIC_FALLBACK_KEYWORD.get(topic_slug, "tech")
    return [fallback]
