import re

from bot.services.category import normalize_category_name
from bot.services.library_groups import normalize_library_group


def parse_link_input(text: str) -> dict:
    lines = text.strip().split("\n")
    url = ""
    tags = []
    priority = "medium"
    category = ""
    library_group_override = ""
    notes = []

    url_pattern = re.compile(r"https?://\S+")
    tag_pattern = re.compile(r"#(\w+)")
    priority_pattern = re.compile(r"!(high|medium|low)", re.IGNORECASE)
    category_pattern = re.compile(r"@(\w+)")
    library_group_pattern = re.compile(r"(?<!\S)~([a-zA-Z0-9-]+)(?!\S)")

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

        for group_match in library_group_pattern.finditer(line):
            normalized_group = normalize_library_group(group_match.group(1))
            if normalized_group:
                library_group_override = normalized_group

        remaining = line
        remaining = url_pattern.sub("", remaining)
        remaining = tag_pattern.sub("", remaining)
        remaining = priority_pattern.sub("", remaining)
        remaining = category_pattern.sub("", remaining)
        remaining = library_group_pattern.sub("", remaining)
        remaining = remaining.strip()
        if remaining and not remaining.startswith("http"):
            notes.append(remaining)

    return {
        "url": url,
        "tags": list(set(tags)),
        "priority": priority,
        "category": category,
        "notes": " ".join(notes),
        "library_group_override": library_group_override,
    }


def _match_category(input_cat: str) -> str:
    return normalize_category_name(input_cat)
