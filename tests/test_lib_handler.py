from types import SimpleNamespace

import pytest

from bot.handlers import lib as lib_module


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


class _FakeMirrorSheet:
    def __init__(self, title: str, records=None):
        self.title = title
        self._records = list(records or [])

    def get_all_records(self):
        return list(self._records)


class _FakeSheetsService:
    def __init__(self, records, mirror_records=None):
        self.records = list(records)
        self.mirror = _FakeMirrorSheet("LIB_shadcn", records=mirror_records or [])
        self.ensure_calls = []
        self.upsert_calls = []
        self.remove_calls = []

    def get_all_records(self):
        return list(self.records)

    def filter_by_library_group(self, group: str):
        group_key = group.lower()
        return [
            r
            for r in self.records
            if str(r.get("Library Group", "")).strip().lower() == group_key
        ]

    def ensure_library_sheet(self, group: str):
        self.ensure_calls.append(group)
        return self.mirror

    def upsert_library_row(self, record: dict):
        self.upsert_calls.append(record)

    def remove_library_row(self, row_id: str, group: str):
        self.remove_calls.append((row_id, group))


def _setup_lang(monkeypatch, lang: str = "en"):
    fake_settings = _FakeSettingsService(lang=lang)
    monkeypatch.setattr(lib_module, "_get_settings_service", lambda: fake_settings)


def _setup_sheets(monkeypatch, sheets: _FakeSheetsService):
    monkeypatch.setattr(lib_module, "get_sheets_service", lambda: sheets)


@pytest.mark.asyncio
async def test_lib_lists_groups_with_counts(monkeypatch):
    _setup_lang(monkeypatch, "en")
    sheets = _FakeSheetsService(
        [
            {"ID": "1", "Library Group": "shadcn"},
            {"ID": "2", "Library Group": "icons"},
            {"ID": "3", "Library Group": ""},
        ]
    )
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=[]))

    response = update.message.replies[0]
    assert "Library groups" in response["text"]
    assert "Total links: <b>3</b>" in response["text"]
    assert "<code>shadcn</code>: 1" in response["text"]
    assert "<code>icons</code>: 1" in response["text"]
    assert "<code>utils</code>: 1" in response["text"]
    assert response["kwargs"]["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_lib_group_rejects_invalid_value(monkeypatch):
    _setup_lang(monkeypatch, "en")
    _setup_sheets(monkeypatch, _FakeSheetsService([]))
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=["not-a-group"]))

    response = update.message.replies[0]["text"]
    assert "Invalid group" in response
    assert "Valid groups:" in response


@pytest.mark.asyncio
async def test_lib_group_returns_summary_preview(monkeypatch):
    _setup_lang(monkeypatch, "en")
    sheets = _FakeSheetsService(
        [
            {"ID": "1", "Library Group": "shadcn", "Tieu de": "Button", "Nguon": "ui.shadcn.com"},
            {"ID": "2", "Library Group": "shadcn", "Tieu de": "Card", "Nguon": "ui.shadcn.com"},
            {"ID": "3", "Library Group": "icons", "Tieu de": "Lucide", "Nguon": "lucide.dev"},
        ]
    )
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=["shadcn"]))

    text = update.message.replies[0]["text"]
    assert "Group: shadcn" in text
    assert "Found <b>2</b> results" in text
    assert "<code>#1</code> Button" in text
    assert "<code>#2</code> Card" in text


@pytest.mark.asyncio
async def test_lib_sheet_ensures_mirror_backfills_and_cleans(monkeypatch):
    _setup_lang(monkeypatch, "en")
    sheets = _FakeSheetsService(
        [
            {"ID": "1", "Library Group": "shadcn", "Tieu de": "Button"},
            {"ID": "2", "Library Group": "shadcn", "Tieu de": "Card"},
            {"ID": "3", "Library Group": "icons", "Tieu de": "Lucide"},
        ],
        mirror_records=[{"ID": "1"}, {"ID": "99"}],
    )
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=["sheet", "shadcn"]))

    text = update.message.replies[0]["text"]
    assert sheets.ensure_calls == ["shadcn"]
    assert [record["ID"] for record in sheets.upsert_calls] == ["1", "2"]
    assert sheets.remove_calls == [("99", "shadcn")]
    assert "Synced sheet LIB_shadcn" in text
    assert "Backfill: 2 | Cleanup: 1" in text


@pytest.mark.asyncio
async def test_lib_sheet_requires_valid_group(monkeypatch):
    _setup_lang(monkeypatch, "en")
    sheets = _FakeSheetsService([])
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=["sheet", "unknown"]))

    text = update.message.replies[0]["text"]
    assert "Invalid group: unknown" in text
    assert sheets.ensure_calls == []
