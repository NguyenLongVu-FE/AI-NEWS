import json
import re

import requests
from bs4 import BeautifulSoup

from bot.utils.source_detect import detect_source


class ScraperService:
    _TIKTOK_PLACEHOLDER_TITLES = {
        "tiktok",
        "tiktok - make your day",
        "tiktok - trends start here",
    }
    _TIKTOK_HASHTAG_RE = re.compile(r"#([^\s#.,;:!?()\[\]{}]{2,40})")
    _TIKTOK_CREATOR_RE = re.compile(r"@([a-zA-Z0-9._-]{2,30})")

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.headers = {"User-Agent": "Mozilla/5.0 (compatible; InfoSaverBot/1.0)"}

    def fetch_metadata(self, url: str) -> dict:
        source = detect_source(url)
        keyword_hints: list[str] = []
        try:
            response = requests.get(
                url, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            title = self._extract_title(soup)
            description = self._extract_description(soup)
            thumbnail = self._extract_thumbnail(soup)
            if source == "TikTok":
                title, description, thumbnail, keyword_hints = self._extract_tiktok_metadata(
                    soup=soup,
                    url=url,
                    title=title,
                    description=description,
                    thumbnail=thumbnail,
                )

            return {
                "title": title or url,
                "description": description,
                "thumbnail": thumbnail,
                "source": source,
                "success": True,
                "error": None,
                "keywords_hint": keyword_hints,
            }
        except requests.RequestException as e:
            if source == "TikTok":
                return self._build_tiktok_oembed_fallback(url=url, source=source, error=str(e))
            return {
                "title": url,
                "description": "",
                "thumbnail": "",
                "source": source,
                "success": False,
                "error": str(e),
                "keywords_hint": [],
            }

    def _extract_title(self, soup) -> str:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        return ""

    def _extract_description(self, soup) -> str:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"]
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"]
        return ""

    def _extract_thumbnail(self, soup) -> str:
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]
        return ""

    def _extract_tiktok_metadata(
        self,
        *,
        soup,
        url: str,
        title: str,
        description: str,
        thumbnail: str,
    ) -> tuple[str, str, str, list[str]]:
        hyd_title, hyd_description, hyd_thumbnail = (
            self._extract_tiktok_hydration_metadata(soup)
        )
        if (not title or self._is_tiktok_placeholder_title(title)) and hyd_title:
            title = hyd_title
        if not description and hyd_description:
            description = hyd_description
        if not thumbnail and hyd_thumbnail:
            thumbnail = hyd_thumbnail

        needs_oembed = (
            not title
            or self._is_tiktok_placeholder_title(title)
            or not description
            or not thumbnail
        )
        if not needs_oembed:
            keywords_hint = self._extract_tiktok_keyword_hints(title, description, url)
            return title, description, thumbnail, keywords_hint

        oembed_payload = self._fetch_tiktok_oembed(url)
        oembed_title = self._as_text(oembed_payload.get("title"))
        oembed_thumbnail = self._as_text(oembed_payload.get("thumbnail_url"))
        oembed_author = self._as_text(oembed_payload.get("author_name"))

        if (not title or self._is_tiktok_placeholder_title(title)) and oembed_title:
            title = oembed_title
        if not description and oembed_title:
            description = oembed_title
        if description and oembed_author and oembed_author.lower() not in description.lower():
            description = f"{description} | Tác giả: {oembed_author}"
        if not thumbnail and oembed_thumbnail:
            thumbnail = oembed_thumbnail

        keywords_hint = self._extract_tiktok_keyword_hints(title, description, url)
        return title, description, thumbnail, keywords_hint

    def _extract_tiktok_hydration_metadata(self, soup) -> tuple[str, str, str]:
        hydration_payload = self._extract_tiktok_hydration_payload(soup)
        if not hydration_payload:
            return "", "", ""

        default_scope = hydration_payload.get("__DEFAULT_SCOPE__")
        if not isinstance(default_scope, dict):
            return "", "", ""
        video_detail = default_scope.get("webapp.video-detail")
        if not isinstance(video_detail, dict):
            return "", "", ""

        share_meta = video_detail.get("shareMeta")
        if not isinstance(share_meta, dict):
            share_meta = {}
        item_info = video_detail.get("itemInfo")
        if not isinstance(item_info, dict):
            item_info = {}
        item_struct = item_info.get("itemStruct")
        if not isinstance(item_struct, dict):
            item_struct = {}
        video_struct = item_struct.get("video")
        if not isinstance(video_struct, dict):
            video_struct = {}

        title = self._as_text(share_meta.get("title"))
        description = self._as_text(share_meta.get("desc"))
        thumbnail = self._as_text(
            video_struct.get("cover") or video_struct.get("originCover")
        )
        return title, description, thumbnail

    def _extract_tiktok_hydration_payload(self, soup) -> dict:
        hydration_script = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
        if hydration_script is None:
            return {}

        payload_text = hydration_script.string or hydration_script.get_text()
        if not payload_text:
            return {}

        try:
            parsed_payload = json.loads(payload_text)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed_payload, dict):
            return parsed_payload
        return {}

    def _fetch_tiktok_oembed(self, url: str) -> dict:
        try:
            response = requests.get(
                "https://www.tiktok.com/oembed",
                params={"url": url},
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException:
            return {}

        try:
            payload = response.json()
        except ValueError:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}

    def _build_tiktok_oembed_fallback(self, *, url: str, source: str, error: str) -> dict:
        oembed_payload = self._fetch_tiktok_oembed(url)
        title = self._as_text(oembed_payload.get("title"))
        description = title
        author_name = self._as_text(oembed_payload.get("author_name"))
        if description and author_name and author_name.lower() not in description.lower():
            description = f"{description} | Tác giả: {author_name}"
        thumbnail = self._as_text(oembed_payload.get("thumbnail_url"))
        keywords_hint = self._extract_tiktok_keyword_hints(title, description, url)
        has_content = bool(title or description or thumbnail)

        return {
            "title": title or url,
            "description": description,
            "thumbnail": thumbnail,
            "source": source,
            "success": has_content,
            "error": None if has_content else error,
            "keywords_hint": keywords_hint,
        }

    def _extract_tiktok_keyword_hints(self, title: str, description: str, url: str) -> list[str]:
        hints = []
        hints.extend(self._extract_hashtags(title))
        hints.extend(self._extract_hashtags(description))
        creator_match = self._TIKTOK_CREATOR_RE.search(str(url or ""))
        if creator_match:
            hints.append(creator_match.group(1))
        return self._deduplicate_preserve_order(hints)

    def _extract_hashtags(self, text: str) -> list[str]:
        return [tag.strip().lstrip("#") for tag in self._TIKTOK_HASHTAG_RE.findall(str(text or ""))]

    def _deduplicate_preserve_order(self, values: list[str]) -> list[str]:
        deduped = []
        seen = set()
        for value in values:
            token = self._as_text(value).lstrip("#")
            key = token.lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(token)
        return deduped

    def _is_tiktok_placeholder_title(self, title: str) -> bool:
        normalized_title = title.strip().lower()
        return normalized_title in self._TIKTOK_PLACEHOLDER_TITLES

    def _as_text(self, value) -> str:
        if isinstance(value, str):
            return value.strip()
        return ""
