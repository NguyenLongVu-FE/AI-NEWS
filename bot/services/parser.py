import re

from bot.services.category import normalize_category_name


def parse_link_input(text: str) -> dict:
    lines = text.strip().split("\n")
    url = ""
    tags = []
    category = ""
    notes = []

    url_pattern = re.compile(r"https?://\S+")
    tag_pattern = re.compile(r"#([a-zA-Z0-9_-]+)")
    category_pattern = re.compile(r"@([a-zA-Z0-9_-]+)")
    priority_pattern = re.compile(r"!(high|medium|low)", re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        url_match = url_pattern.search(line)
        if url_match and not url:
            url = url_match.group(0)

        tag_matches = tag_pattern.findall(line)
        tags.extend(tag_matches)

        category_match = category_pattern.search(line)
        if category_match:
            cat = category_match.group(1)
            category = _match_category(cat)

        remaining = line
        remaining = url_pattern.sub("", remaining)
        remaining = tag_pattern.sub("", remaining)
        remaining = category_pattern.sub("", remaining)
        remaining = priority_pattern.sub("", remaining)
        remaining = remaining.strip()
        if remaining and not remaining.startswith("http"):
            notes.append(remaining)

    return {
        "url": url,
        "tags": list(set(tags)),
        "category": category,
        "notes": " ".join(notes),
    }


def _match_category(input_cat: str) -> str:
    return normalize_category_name(input_cat)
