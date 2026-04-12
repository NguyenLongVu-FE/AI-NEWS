import re
from html import escape

MAX_NOTE_LENGTH = 500
MAX_TAGS = 10
URL_PATTERN = re.compile(r"^https?://[^\s<>'\"{}|\\^`]+$")


def validate_url(url: str) -> tuple:
    if not url:
        return False, "URL is empty"
    if len(url) > 2048:
        return False, "URL too long (max 2048 chars)"
    if not URL_PATTERN.match(url):
        return False, "Invalid URL format. Must start with http:// or https://"
    return True, ""


def sanitize_html(text: str) -> str:
    return escape(str(text))


def validate_note(note: str) -> tuple:
    if len(note) > MAX_NOTE_LENGTH:
        return False, f"Note too long ({len(note)}/{MAX_NOTE_LENGTH} chars)"
    return True, ""


def validate_tags(tags: list) -> tuple:
    if len(tags) > MAX_TAGS:
        return False, f"Too many tags ({len(tags)}/{MAX_TAGS})"
    for tag in tags:
        if len(tag) > 30:
            return False, f"Tag too long: {tag[:20]}..."
    return True, ""
