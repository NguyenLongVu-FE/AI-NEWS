from urllib.parse import urlparse


def detect_source(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "tiktok.com" in domain:
        return "TikTok"
    if "youtube.com" in domain or "youtu.be" in domain:
        return "YouTube"
    if "facebook.com" in domain or "fb.watch" in domain:
        return "Facebook"
    if "twitter.com" in domain or "x.com" in domain:
        return "Twitter/X"
    return "Web"
