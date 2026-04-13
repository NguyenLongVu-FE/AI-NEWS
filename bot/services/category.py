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
    ),
    "FE": (
        "frontend",
        "front-end",
        "front end",
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
        "component",
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
    "FE",
    "UIUX",
    "Design",
    "Marketing",
    "Business",
    "Education",
    "Health",
    "Entertainment",
    "Tech",
]

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


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


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
    content = f"{url} {title} {description} {summary} {tags_text}".lower()

    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in content)
        if score > 0:
            scores[category] = score

    if scores:
        best_score = max(scores.values())
        for category in CATEGORY_PRIORITY:
            if scores.get(category) == best_score:
                return category

    return "Tech"
