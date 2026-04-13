from types import SimpleNamespace

import pytest

from bot.handlers import topics as topics_module


class _DummyMessage:
    def __init__(self, user_id: int = 123):
        self.from_user = SimpleNamespace(id=user_id)
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append({"text": text, "kwargs": kwargs})


class _DummyUpdate:
    def __init__(self):
        self.message = _DummyMessage()


class _DummyContext:
    def __init__(self, args=None):
        self.args = args or []


class _FakeSettingsService:
    def __init__(self, lang: str = "en"):
        self.lang = lang

    def get_user_settings(self, _user_id: str) -> dict:
        return {"language": self.lang}


class _FakeSheetsService:
    def __init__(self, counts):
        self._counts = counts

    def list_topic_counts(self):
        return dict(self._counts)


def _setup_lang(monkeypatch, lang: str = "en"):
    fake_settings = _FakeSettingsService(lang=lang)
    monkeypatch.setattr(topics_module, "settings_service", fake_settings)


def _setup_sheets(monkeypatch, sheets: _FakeSheetsService):
    monkeypatch.setattr(topics_module, "get_sheets_service", lambda: sheets)


@pytest.mark.asyncio
async def test_topics_lists_counts(monkeypatch):
    _setup_lang(monkeypatch, "en")
    _setup_sheets(
        monkeypatch,
        _FakeSheetsService({"AI Agent": 2, "FE": 1}),
    )
    update = _DummyUpdate()

    await topics_module.topics_cmd(update, _DummyContext(args=[]))

    response = update.message.replies[0]
    assert "Topics" in response["text"]
    assert "Total links: <b>3</b>" in response["text"]
    assert "<b>AI Agent</b>: 2" in response["text"]
    assert "<b>FE</b>: 1" in response["text"]
    assert response["kwargs"]["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_topics_empty_state(monkeypatch):
    _setup_lang(monkeypatch, "en")
    _setup_sheets(monkeypatch, _FakeSheetsService({}))
    update = _DummyUpdate()

    await topics_module.topics_cmd(update, _DummyContext(args=[]))

    response = update.message.replies[0]
    assert "No content found" in response["text"]
    assert "No topics yet." in response["text"]
