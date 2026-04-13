import re
from typing import Iterable, Optional


_SLUG_RE = re.compile(r"[^a-z0-9]+")

GLOBAL_KEYWORD_RULES = {
    "shadcn": "shadcn",
    "figma": "figma",
    "tailwind": "tailwind",
    "react": "react",
    "nextjs": "nextjs",
    "next.js": "nextjs",
    "telegram": "telegram",
    "python": "python",
}

TOPIC_KEYWORD_RULES = {
    "ai-agent": {
        "ai agent": "ai-agent",
        "agentic": "agentic",
        "skill": "skill",
        "plan": "plan",
        "tool calling": "tool-calling",
        "langgraph": "langgraph",
        "crewai": "crewai",
    }
}


def normalize_keyword(value: str) -> str:
    return _SLUG_RE.sub("-", str(value or "").strip().lower()).strip("-")


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


def detect_keywords(
    url: str,
    title: str = "",
    summary: str = "",
    topic: str = "",
    manual_keywords: Optional[Iterable[str]] = None,
) -> list[str]:
    content = f"{url} {title} {summary}".lower()
    detected: list[str] = []

    for needle, keyword in GLOBAL_KEYWORD_RULES.items():
        if needle in content:
            detected.append(keyword)

    topic_slug = normalize_keyword(topic)
    for needle, keyword in TOPIC_KEYWORD_RULES.get(topic_slug, {}).items():
        if needle in content:
            detected.append(keyword)

    if topic_slug == "ai-agent":
        detected.append("ai-agent")

    if manual_keywords:
        detected.extend(str(keyword) for keyword in manual_keywords)

    return normalize_keywords(detected)
