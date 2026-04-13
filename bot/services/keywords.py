import re
import unicodedata
from collections import Counter
from typing import Iterable, Optional


_SLUG_RE = re.compile(r"[^a-z0-9]+")
_WORD_RE = re.compile(r"[a-z0-9]+")
_TECH_TOKEN_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9]*(?:[.+#-][a-zA-Z0-9]+)+\b")
_MAX_KEYWORDS = 15

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "va",
    "la",
    "cho",
    "trong",
    "mot",
    "nhung",
    "cac",
    "duoc",
    "khi",
    "de",
    "ve",
    "tren",
    "tu",
    "day",
    "ban",
    "cua",
    "nhung",
    "dang",
    "co",
    "se",
    "giup",
    "theo",
    "vao",
    "nhu",
    "toi",
    "tao",
    "cach",
    "huong",
    "dan",
    "xay",
    "dung",
    "voi",
    "guide",
    "thong",
    "tin",
    "bai",
    "viet",
    "cap",
    "nhat",
    "quy",
}

_SUMMARY_HINT_TERMS = {
    "ai",
    "agent",
    "agentic",
    "skill",
    "plan",
    "planning",
    "workflow",
    "prompt",
    "template",
    "model",
    "llm",
    "rag",
    "tool",
    "tools",
    "calling",
    "automation",
    "orchestrator",
    "orchestration",
    "langgraph",
    "crewai",
    "autogen",
    "telegram",
    "webhook",
    "api",
    "dashboard",
    "keyword",
    "filter",
    "summary",
}

_NO_SUMMARY_MARKERS = {
    "chua co tom tat",
    "no summary",
    "no summary yet",
}

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


def _extract_summary_keywords(summary: str) -> list[str]:
    raw_summary = str(summary or "").strip()
    if not raw_summary:
        return []

    detected: list[str] = []

    for token in _TECH_TOKEN_RE.findall(raw_summary):
        normalized = normalize_keyword(token)
        if normalized:
            detected.append(normalized)

    normalized_summary = unicodedata.normalize("NFKD", raw_summary.lower())
    ascii_summary = "".join(
        ch for ch in normalized_summary if not unicodedata.combining(ch)
    )
    compact_summary = re.sub(r"\s+", " ", ascii_summary).strip()
    if compact_summary in _NO_SUMMARY_MARKERS:
        return []

    words: list[str] = []
    for word in _WORD_RE.findall(ascii_summary):
        if word in _STOPWORDS or word.isdigit():
            continue
        if len(word) < 4 and word not in _SUMMARY_HINT_TERMS:
            continue
        words.append(word)

    if not words:
        return normalize_keywords(detected)[:_MAX_KEYWORDS]

    counts = Counter(words)
    frequent_words = [
        word
        for word, count in counts.most_common(30)
        if count >= 2 or word in _SUMMARY_HINT_TERMS
    ]
    if not frequent_words:
        seen_words = set()
        for word in words:
            if word in seen_words:
                continue
            seen_words.add(word)
            frequent_words.append(word)
            if len(frequent_words) >= 8:
                break

    bigrams: list[str] = []
    for idx in range(len(words) - 1):
        left = words[idx]
        right = words[idx + 1]
        if left in _STOPWORDS or right in _STOPWORDS:
            continue
        if left in _SUMMARY_HINT_TERMS or right in _SUMMARY_HINT_TERMS:
            phrase = normalize_keyword(f"{left} {right}")
            if phrase:
                bigrams.append(phrase)

    detected.extend(bigrams[:6])
    detected.extend(frequent_words[:10])
    return normalize_keywords(detected)[:_MAX_KEYWORDS]


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

    detected.extend(_extract_summary_keywords(summary))

    if topic_slug:
        detected.append(topic_slug)

    if manual_keywords:
        detected.extend(str(keyword) for keyword in manual_keywords)

    normalized = normalize_keywords(detected)[:_MAX_KEYWORDS]
    if normalized:
        return normalized
    return ["tech"]
