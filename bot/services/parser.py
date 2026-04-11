import re

from bot.config import CATEGORIES


def parse_link_input(text: str) -> dict:
    lines = text.strip().split("\n")
    url = ""
    tags = []
    priority = "medium"
    category = ""
    notes = []

    url_pattern = re.compile(r"https?://\S+")
    tag_pattern = re.compile(r"#(\w+)")
    priority_pattern = re.compile(r"!(high|medium|low)", re.IGNORECASE)
    category_pattern = re.compile(r"@(\w+)")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        url_match = url_pattern.search(line)
        if url_match and not url:
            url = url_match.group(0)

        tag_matches = tag_pattern.findall(line)
        tags.extend(tag_matches)

        priority_match = priority_pattern.search(line)
        if priority_match:
            priority = priority_match.group(1).lower()

        category_match = category_pattern.search(line)
        if category_match:
            cat = category_match.group(1)
            category = _match_category(cat)

        remaining = line
        remaining = url_pattern.sub("", remaining)
        remaining = tag_pattern.sub("", remaining)
        remaining = priority_pattern.sub("", remaining)
        remaining = category_pattern.sub("", remaining)
        remaining = remaining.strip()
        if remaining and not remaining.startswith("http"):
            notes.append(remaining)

    return {
        "url": url,
        "tags": list(set(tags)),
        "priority": priority,
        "category": category or "Other",
        "notes": " ".join(notes),
    }


def _match_category(input_cat: str) -> str:
    input_lower = input_cat.lower()
    for cat in CATEGORIES:
        if cat.lower() == input_lower:
            return cat
    return input_cat.capitalize()
