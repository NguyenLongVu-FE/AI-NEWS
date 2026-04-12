import importlib
import sys
from types import SimpleNamespace

import pytest

from bot.config import SHEET_HEADERS


def _load_handler_module(monkeypatch, module_name: str, fake_sheets):
    import bot.services.gemini as gemini_module
    import bot.services.scraper as scraper_module
    import bot.services.settings as settings_module
    import bot.services.sheets as sheets_module

    class _FakeSettingsService:
        def __init__(self):
            pass

        def get_user_settings(self, _user_id: str) -> dict:
            return {"language": "en"}

    class _FakeScraperService:
        def fetch_metadata(self, _url: str) -> dict:
            return {
                "title": "",
                "description": "",
                "thumbnail": "",
                "source": "",
                "success": True,
                "error": None,
            }

    class _FakeGeminiService:
        def summarize(self, _title: str, _description: str, _url: str) -> str:
            return ""

    monkeypatch.setattr(sheets_module, "get_sheets_service", lambda: fake_sheets)
    monkeypatch.setattr(settings_module, "SettingsService", _FakeSettingsService)
    monkeypatch.setattr(scraper_module, "ScraperService", _FakeScraperService)
    monkeypatch.setattr(gemini_module, "GeminiService", _FakeGeminiService)

    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


class _DummyEditableMessage:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, **kwargs):
        self.edits.append({"text": text, "kwargs": kwargs})


class _DummyMessage:
    def __init__(self, text: str = "", user_id: int = 123):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id, first_name="Tester")
        self.replies = []
        self.editables = []

    async def reply_text(self, text, **kwargs):
        editable = _DummyEditableMessage()
        self.replies.append({"text": text, "kwargs": kwargs})
        self.editables.append(editable)
        return editable


class _DummyUpdate:
    def __init__(self, text: str = ""):
        self.message = _DummyMessage(text=text)


class _DummyContext:
    def __init__(self, args=None):
        self.args = args or []


class _DummyQuery:
    def __init__(self, data: str, user_id: int = 123):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.answer_calls = 0
        self.edits = []

    async def answer(self):
        self.answer_calls += 1

    async def edit_message_text(self, text, **kwargs):
        self.edits.append({"text": text, "kwargs": kwargs})


class _DummyCallbackUpdate:
    def __init__(self, data: str):
        self.callback_query = _DummyQuery(data=data)


class _LinkSheets:
    def __init__(self, upsert_raises: bool = False):
        self.upsert_raises = upsert_raises
        self.append_kwargs = None
        self.upsert_records = []
        self.get_row_calls = []

    def find_by_url(self, _url: str):
        return None

    def append_link(self, **kwargs):
        self.append_kwargs = dict(kwargs)
        return 9

    def get_row(self, row: int):
        self.get_row_calls.append(row)
        return {
            "ID": "9",
            "Library Group": self.append_kwargs.get("library_group", ""),
            "Tieu de": "Button docs",
        }

    def upsert_library_row(self, record: dict):
        self.upsert_records.append(dict(record))
        if self.upsert_raises:
            raise RuntimeError("mirror sync failed")


class _ManageSheets:
    def __init__(self):
        self.update_cell_calls = []
        self.remove_calls = []
        self.upsert_calls = []

    def get_row(self, _row: int):
        return {"ID": "15", "Library Group": "icons", "Tieu de": "Lucide"}

    def update_cell(self, row: int, col: int, value: str):
        self.update_cell_calls.append((row, col, value))

    def remove_library_row(self, row_id: str, group: str):
        self.remove_calls.append((row_id, group))

    def upsert_library_row(self, record: dict):
        self.upsert_calls.append(dict(record))


class _CallbackSheets:
    def __init__(self):
        self.deleted_rows = []
        self.remove_calls = []

    def get_row(self, _row: int):
        return {"ID": "7", "Library Group": "icons", "Tieu de": "Icon docs"}

    def delete_row(self, row: int):
        self.deleted_rows.append(row)

    def remove_library_row(self, row_id: str, group: str):
        self.remove_calls.append((row_id, group))


@pytest.mark.asyncio
async def test_link_save_sync_uses_override_and_mirror_upsert_is_non_blocking(monkeypatch):
    sheets = _LinkSheets(upsert_raises=True)
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    monkeypatch.setattr(
        link_module,
        "parse_link_input",
        lambda _text: {
            "url": "https://ui.shadcn.com/docs/components/button",
            "tags": [],
            "priority": "medium",
            "category": "Other",
            "notes": "note",
            "library_group_override": "ShAdCn",
        },
    )
    monkeypatch.setattr(link_module, "validate_url", lambda _url: (True, ""))
    monkeypatch.setattr(link_module, "validate_tags", lambda _tags: (True, ""))
    monkeypatch.setattr(link_module, "sanitize_html", lambda value: value)
    monkeypatch.setattr(
        link_module.scraper,
        "fetch_metadata",
        lambda _url: {
            "title": "shadcn button",
            "description": "docs",
            "thumbnail": "thumb.png",
            "source": "ui.shadcn.com",
            "success": True,
            "error": None,
        },
    )
    monkeypatch.setattr(link_module.gemini, "summarize", lambda *_args: "summary")
    monkeypatch.setattr(
        link_module,
        "detect_library_group",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("fallback detect should not run when override is valid")
        ),
    )

    update = _DummyUpdate(text="https://ui.shadcn.com/docs/components/button")
    await link_module.handle_link(update, _DummyContext())

    assert sheets.append_kwargs["library_group"] == "shadcn"
    assert sheets.get_row_calls == [9]
    assert len(sheets.upsert_records) == 1
    assert update.message.editables[0].edits
    assert "Saved successfully!" in update.message.editables[0].edits[0]["text"]


@pytest.mark.asyncio
async def test_edit_library_group_moves_between_mirror_sheets(monkeypatch):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    context = _DummyContext(args=["15", "library_group", "ShAdCn"])
    await manage_module.edit_cmd(update, context)

    group_col = SHEET_HEADERS.index("Library Group") + 1
    assert sheets.update_cell_calls == [(15, group_col, "shadcn")]
    assert sheets.remove_calls == [("15", "icons")]
    assert len(sheets.upsert_calls) == 1
    assert sheets.upsert_calls[0]["Library Group"] == "shadcn"
    assert "library_group: → shadcn" in update.message.replies[0]["text"]


@pytest.mark.asyncio
async def test_delete_callback_removes_mirror_row(monkeypatch):
    sheets = _CallbackSheets()
    callback_module = _load_handler_module(monkeypatch, "bot.handlers.callback", sheets)
    monkeypatch.setattr(callback_module, "_get_lang", lambda _query: "en")

    update = _DummyCallbackUpdate("c:del:7:y")
    await callback_module.handle_callback(update, _DummyContext())

    assert update.callback_query.answer_calls == 1
    assert sheets.deleted_rows == [7]
    assert sheets.remove_calls == [("7", "icons")]
    assert update.callback_query.edits
    assert "Deleted!" in update.callback_query.edits[0]["text"]
