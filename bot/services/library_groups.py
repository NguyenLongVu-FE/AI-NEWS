from urllib.parse import urlparse

from bot.config import LIBRARY_GROUPS

DOMAIN_RULES = {
    "motion.dev": "animation",
    "animejs.com": "animation",
    "ui.shadcn.com": "shadcn",
    "lucide.dev": "icons",
    "tabler-icons.io": "icons",
    "recharts.org": "charts",
    "tanstack.com/table": "table",
}

KEYWORD_RULES = {
    "framer motion": "animation",
    "gsap": "animation",
    "shadcn": "shadcn",
    "react hook form": "forms",
    "zod": "forms",
    "zustand": "state-management",
    "redux": "state-management",
}


def normalize_library_group(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    return key if key in LIBRARY_GROUPS else None


def detect_library_group(url: str, title: str = "", summary: str = "") -> str:
    host = urlparse(url).netloc.lower()
    content = f"{url} {title} {summary}".lower()

    for rule, group in DOMAIN_RULES.items():
        if rule in host or rule in content:
            return group

    for keyword, group in KEYWORD_RULES.items():
        if keyword in content:
            return group

    return "utils"
