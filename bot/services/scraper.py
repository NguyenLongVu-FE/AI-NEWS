import requests
from bs4 import BeautifulSoup

from bot.utils.source_detect import detect_source


class ScraperService:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.headers = {"User-Agent": "Mozilla/5.0 (compatible; InfoSaverBot/1.0)"}

    def fetch_metadata(self, url: str) -> dict:
        source = detect_source(url)
        try:
            response = requests.get(
                url, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            title = self._extract_title(soup)
            description = self._extract_description(soup)
            thumbnail = self._extract_thumbnail(soup)

            return {
                "title": title or url,
                "description": description,
                "thumbnail": thumbnail,
                "source": source,
                "success": True,
                "error": None,
            }
        except requests.RequestException as e:
            return {
                "title": url,
                "description": "",
                "thumbnail": "",
                "source": source,
                "success": False,
                "error": str(e),
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
