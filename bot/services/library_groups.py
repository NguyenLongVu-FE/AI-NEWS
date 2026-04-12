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
    parsed_url = urlparse(url)
    host = (parsed_url.hostname or "").lower()
    path = (parsed_url.path or "").lower().rstrip("/")
    content = f"{url} {title} {summary}".lower()

    for rule, group in DOMAIN_RULES.items():
        parsed_rule = urlparse(f"https://{rule}")
        rule_host = (parsed_rule.hostname or "").lower()
        rule_path = (parsed_rule.path or "").lower().rstrip("/")
        if not rule_host:
            continue
        if host != rule_host and not host.endswith(f".{rule_host}"):
            continue
        if rule_path and path != rule_path and not path.startswith(f"{rule_path}/"):
            continue
        return group

    for keyword, group in KEYWORD_RULES.items():
        if keyword in content:
            return group

    return "utils"
