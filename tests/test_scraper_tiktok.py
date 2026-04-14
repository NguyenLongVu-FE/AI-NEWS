import json

import requests

import bot.services.scraper as scraper_module
from bot.services.scraper import ScraperService


class _FakeResponse:
    def __init__(self, *, text: str = "", status_code: int = 200, json_data=None):
        self.text = text
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON payload")
        return self._json_data


def test_fetch_metadata_uses_open_graph_fields(monkeypatch):
    html = """
    <html>
      <head>
        <meta property="og:title" content="Example title" />
        <meta property="og:description" content="Example description" />
        <meta property="og:image" content="https://example.com/thumb.jpg" />
      </head>
    </html>
    """

    def fake_get(_url, headers=None, timeout=None, params=None):
        return _FakeResponse(text=html)

    monkeypatch.setattr(scraper_module.requests, "get", fake_get)

    metadata = ScraperService().fetch_metadata("https://example.com/story")

    assert metadata["success"] is True
    assert metadata["source"] == "Web"
    assert metadata["title"] == "Example title"
    assert metadata["description"] == "Example description"
    assert metadata["thumbnail"] == "https://example.com/thumb.jpg"


def test_fetch_metadata_tiktok_uses_hydration_payload(monkeypatch):
    tiktok_url = "https://www.tiktok.com/@creator/video/123456"
    hydration_payload = {
        "__DEFAULT_SCOPE__": {
            "webapp.video-detail": {
                "shareMeta": {
                    "title": "Creator on TikTok",
                    "desc": "A TikTok caption from hydration",
                },
                "itemInfo": {
                    "itemStruct": {"video": {"cover": "https://cdn.example.com/cover.jpg"}}
                },
            }
        }
    }
    html = (
        "<html><head><title>TikTok - Make Your Day</title>"
        f"<script id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\" type=\"application/json\">{json.dumps(hydration_payload)}</script>"
        "</head></html>"
    )
    calls = []

    def fake_get(url, headers=None, timeout=None, params=None):
        calls.append((url, params))
        return _FakeResponse(text=html)

    monkeypatch.setattr(scraper_module.requests, "get", fake_get)

    metadata = ScraperService().fetch_metadata(tiktok_url)

    assert metadata["success"] is True
    assert metadata["source"] == "TikTok"
    assert metadata["title"] == "Creator on TikTok"
    assert metadata["description"] == "A TikTok caption from hydration"
    assert metadata["thumbnail"] == "https://cdn.example.com/cover.jpg"
    assert calls == [(tiktok_url, None)]


def test_fetch_metadata_tiktok_falls_back_to_oembed(monkeypatch):
    tiktok_url = "https://www.tiktok.com/@creator/video/123456"
    html = "<html><head><title>TikTok - Make Your Day</title></head></html>"
    oembed_payload = {
        "title": "A TikTok caption from oEmbed",
        "thumbnail_url": "https://cdn.example.com/oembed-cover.jpg",
    }
    calls = []

    def fake_get(url, headers=None, timeout=None, params=None):
        calls.append((url, params))
        if url == "https://www.tiktok.com/oembed":
            return _FakeResponse(json_data=oembed_payload)
        return _FakeResponse(text=html)

    monkeypatch.setattr(scraper_module.requests, "get", fake_get)

    metadata = ScraperService().fetch_metadata(tiktok_url)

    assert metadata["success"] is True
    assert metadata["title"] == "A TikTok caption from oEmbed"
    assert metadata["description"] == "A TikTok caption from oEmbed"
    assert metadata["thumbnail"] == "https://cdn.example.com/oembed-cover.jpg"
    assert calls == [
        (tiktok_url, None),
        ("https://www.tiktok.com/oembed", {"url": tiktok_url}),
    ]


def test_fetch_metadata_tiktok_uses_oembed_when_page_request_fails(monkeypatch):
    tiktok_url = "https://www.tiktok.com/@creator/video/123456"
    oembed_payload = {
        "title": "Meal prep ideas #mealprep #keto",
        "author_name": "Creator",
        "thumbnail_url": "https://cdn.example.com/oembed-cover.jpg",
    }
    calls = []

    def fake_get(url, headers=None, timeout=None, params=None):
        calls.append((url, params))
        if url == tiktok_url:
            raise requests.RequestException("blocked by upstream")
        if url == "https://www.tiktok.com/oembed":
            return _FakeResponse(json_data=oembed_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(scraper_module.requests, "get", fake_get)

    metadata = ScraperService().fetch_metadata(tiktok_url)

    assert metadata["success"] is True
    assert metadata["source"] == "TikTok"
    assert metadata["title"] == "Meal prep ideas #mealprep #keto"
    assert "Tác giả: Creator" in metadata["description"]
    assert metadata["thumbnail"] == "https://cdn.example.com/oembed-cover.jpg"
    assert metadata["keywords_hint"] == ["mealprep", "keto", "creator"]
    assert calls == [
        (tiktok_url, None),
        ("https://www.tiktok.com/oembed", {"url": tiktok_url}),
    ]
