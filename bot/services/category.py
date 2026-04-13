import re
from typing import Optional, Sequence
from urllib.parse import urlparse

from bot.config import CATEGORIES

DOMAIN_RULES = {
    "figma.com": "UIUX",
    "dribbble.com": "Design",
    "behance.net": "Design",
    "ui.shadcn.com": "FE",
    "react.dev": "FE",
    "nextjs.org": "FE",
    "tailwindcss.com": "FE",
    "developer.mozilla.org": "FE",
    "ahrefs.com": "Marketing",
    "semrush.com": "Marketing",
    "hubspot.com": "Marketing",
    "mailchimp.com": "Marketing",
    "coursera.org": "Education",
    "edx.org": "Education",
    "healthline.com": "Health",
    "who.int": "Health",
    "webmd.com": "Health",
    "techcrunch.com": "Tech",
    "theverge.com": "Tech",
}

CATEGORY_KEYWORDS = {
    "AI Agent": (
        "ai agent",
        "agentic",
        "multi-agent",
        "tool calling",
        "langgraph",
        "crewai",
        "autogen",
        "skill plan",
        "plan-and-execute",
    ),
    "UIUX": (
        "uiux",
        "ui/ux",
        "ux/ui",
        "user experience",
        "usability",
        "wireframe",
        "prototype",
        "interaction design",
        "user flow",
        "design system",
        "accessibility",
        "information architecture",
        "persona",
        "journey map",
        "figma",
    ),
    "FE": (
        "frontend",
        "front-end",
        "front end",
        "web app",
        "webapp",
        "react",
        "next.js",
        "nextjs",
        "vue",
        "angular",
        "tailwind",
        "css",
        "html",
        "javascript",
        "typescript",
        "shadcn",
        "storybook",
    ),
    "Design": (
        "design",
        "design system",
        "typography",
        "color palette",
        "layout",
        "visual design",
        "graphic design",
        "illustration",
        "icon",
        "branding",
    ),
    "Marketing": (
        "marketing",
        "maketing",
        "seo",
        "sem",
        "growth",
        "content strategy",
        "email marketing",
        "social media",
        "conversion",
        "funnel",
        "google ads",
        "facebook ads",
    ),
    "Business": (
        "business",
        "startup",
        "saas",
        "revenue",
        "sales",
        "finance",
        "go-to-market",
        "operation",
        "management",
        "product strategy",
    ),
    "Education": (
        "education",
        "course",
        "lesson",
        "tutorial",
        "learning",
        "study",
        "curriculum",
    ),
    "Health": (
        "health",
        "fitness",
        "nutrition",
        "wellness",
        "medical",
        "medicine",
        "mental health",
    ),
    "Entertainment": (
        "entertainment",
        "music",
        "movie",
        "film",
        "game",
        "gaming",
        "anime",
        "show",
    ),
    "Tech": (
        "tech",
        "technology",
        "ai",
        "machine learning",
        "llm",
        "software",
        "programming",
        "developer",
        "devops",
        "cloud",
        "api",
        "database",
        "python",
        "golang",
    ),
}

CATEGORY_PRIORITY = [
    "AI Agent",
    "UIUX",
    "FE",
    "Design",
    "Marketing",
    "Business",
    "Education",
    "Health",
    "Entertainment",
    "Tech",
]

_STRONG_CATEGORY_KEYWORDS = {
    "UIUX": {
        "uiux",
        "ui/ux",
        "ux/ui",
        "user experience",
        "wireframe",
        "prototype",
        "interaction design",
        "user flow",
        "design system",
        "accessibility",
        "information architecture",
        "journey map",
        "figma",
    },
    "FE": {
        "frontend",
        "front-end",
        "front end",
        "react",
        "next.js",
        "nextjs",
        "vue",
        "angular",
        "tailwind",
        "typescript",
        "javascript",
        "css",
        "html",
        "shadcn",
        "storybook",
    },
}

_CATEGORY_ALIASES = {
    "tech": "Tech",
    "technology": "Tech",
    "aiagent": "AI Agent",
    "agent": "AI Agent",
    "fe": "FE",
    "frontend": "FE",
    "frontenddev": "FE",
    "uiux": "UIUX",
    "uxui": "UIUX",
    "ui": "UIUX",
    "ux": "UIUX",
    "design": "Design",
    "marketing": "Marketing",
    "maketing": "Marketing",
    "business": "Business",
    "education": "Education",
    "health": "Health",
    "entertainment": "Entertainment",
    "other": "",
}

_MATCH_TEXT_RE = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _normalize_match_text(value: str) -> str:
    return _MATCH_TEXT_RE.sub(" ", str(value or "").strip().lower()).strip()


def _contains_keyword(content: str, keyword: str) -> bool:
    needle = _normalize_match_text(keyword)
    if not needle:
        return False
    return f" {needle} " in f" {content} "


def normalize_category_name(value: Optional[str]) -> str:
    if not value:
        return ""
    key = _slug(value)
    if not key:
        return ""

    alias = _CATEGORY_ALIASES.get(key)
    if alias is not None:
        return alias

    for category in CATEGORIES:
        if _slug(category) == key:
            return category
    return ""


def is_forbidden_other_category(value: Optional[str]) -> bool:
    return _slug(value or "") == "other"


def _score_category(content: str, category: str, keywords: Sequence[str]) -> tuple[int, int]:
    strong_keywords = _STRONG_CATEGORY_KEYWORDS.get(category, set())
    score = 0
    strong_hits = 0
    for keyword in keywords:
        if not _contains_keyword(content, keyword):
            continue
        if keyword in strong_keywords:
            score += 2
            strong_hits += 1
        else:
            score += 1
    return score, strong_hits


def detect_category(
    url: str,
    title: str = "",
    description: str = "",
    summary: str = "",
    tags: Optional[Sequence[str]] = None,
) -> str:
    host = (urlparse(url).hostname or "").lower()
    for domain, category in DOMAIN_RULES.items():
        if host == domain or host.endswith(f".{domain}"):
            return category

    tags_text = " ".join(tag for tag in (tags or []) if tag)
    content = _normalize_match_text(f"{url} {title} {description} {summary} {tags_text}")

    scores = {}
    strong_hits = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score, strong_count = _score_category(content, category, keywords)
        if score > 0:
            scores[category] = score
            strong_hits[category] = strong_count

    fe_score = scores.get("FE", 0)
    if fe_score and strong_hits.get("FE", 0) == 0:
        scores.pop("FE", None)
        strong_hits.pop("FE", None)

    if scores:
        best_score = max(scores.values())
        for category in CATEGORY_PRIORITY:
            if scores.get(category) == best_score:
                return category

    return "Tech"
