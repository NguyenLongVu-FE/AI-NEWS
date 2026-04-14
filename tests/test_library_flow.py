import importlib
import sys
from types import SimpleNamespace

import pytest


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
                "title": "AI Agent plan",
                "description": "skill plan",
                "thumbnail": "thumb.png",
                "source": "example.com",
                "success": True,
                "error": None,
            }

    class _FakeGeminiService:
        def summarize(self, _title: str, _description: str, _url: str) -> str:
            return "AI summary"

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
    def __init__(self, args=None, user_data=None):
        self.args = args or []
        self.user_data = user_data if user_data is not None else {}


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
    def __init__(self, existing_id: str | None = None):
        self.existing_id = existing_id
        self.append_kwargs = None
        self.append_note_calls = []
        self.merge_keyword_calls = []
        self.update_calls = []
        self.move_calls = []
        self.records = {
            "5": {
                "ID": "5",
                "Tieu de": "Existing",
                "Nguoi luu": "Tester",
                "Tags": "skill",
                "Ghi chu tay": "old",
            }
        }

    def find_by_url(self, _url: str):
        return self.existing_id

    def append_link(self, **kwargs):
        self.append_kwargs = dict(kwargs)
        return 9

    def get_row_by_id(self, row_id):
        return dict(self.records.get(str(row_id), {"ID": str(row_id)}))

    def append_note_by_id(self, row_id, note):
        self.append_note_calls.append((row_id, note))
        return True

    def merge_keywords_by_id(self, row_id, keywords):
        self.merge_keyword_calls.append((row_id, list(keywords)))
        return True

    def update_cell_by_id(self, row_id, col, value):
        self.update_calls.append((row_id, col, value))
        record = self.records.setdefault(str(row_id), {"ID": str(row_id)})
        if col == 3:
            record["Tieu de"] = value
        elif col == 7:
            record["Ghi chu tay"] = value
        elif col == 9:
            record["Tags"] = value
        return True

    def move_row_to_topic_by_id(self, row_id, topic):
        self.move_calls.append((row_id, topic))
        record = self.records.setdefault(str(row_id), {"ID": str(row_id)})
        record["Chu de"] = topic
        return True


class _ManageSheets:
    def __init__(self):
        self.update_calls = []
        self.move_calls = []
        self.records = {15: {"ID": "15", "Tieu de": "Old title"}}

    def get_row_by_id(self, row_id):
        return self.records.get(row_id)

    def update_cell_by_id(self, row_id, col, value):
        self.update_calls.append((row_id, col, value))
        return True

    def move_row_to_topic_by_id(self, row_id, topic):
        self.move_calls.append((row_id, topic))
        return True

    def append_note_by_id(self, row_id, note):
        return True

    def delete_row_by_id(self, row_id):
        return True


class _CallbackSheets:
    def __init__(self):
        self.deleted = []
        self.records = {7: {"ID": "7", "Tieu de": "Record"}}

    def get_row_by_id(self, row_id):
        return self.records.get(row_id)

    def delete_row_by_id(self, row_id):
        self.deleted.append(row_id)
        return True


@pytest.mark.asyncio
async def test_link_save_uses_topic_keywords_flow(monkeypatch):
    sheets = _LinkSheets()
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    monkeypatch.setattr(
        link_module,
        "parse_link_input",
        lambda _text: {
            "url": "https://example.com/agent",
            "tags": ["custom"],
            "category": "AI Agent",
            "notes": "note",
        },
    )
    monkeypatch.setattr(link_module, "validate_url", lambda _url: (True, ""))
    monkeypatch.setattr(link_module, "validate_tags", lambda _tags: (True, ""))
    monkeypatch.setattr(link_module, "sanitize_html", lambda value: value)
    monkeypatch.setattr(
        link_module,
        "detect_keywords",
        lambda **_kwargs: ["skill", "plan", "custom"],
    )

    update = _DummyUpdate(text="https://example.com/agent")
    await link_module.handle_link(update, _DummyContext())

    assert sheets.append_kwargs is not None
    assert sheets.append_kwargs["category"] == "AI Agent"
    assert sheets.append_kwargs["tags"] == ["skill", "plan", "custom"]
    assert "Saved successfully!" in update.message.editables[0].edits[0]["text"]


@pytest.mark.asyncio
async def test_link_duplicate_merges_note_and_keywords(monkeypatch):
    sheets = _LinkSheets(existing_id="5")
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    monkeypatch.setattr(
        link_module,
        "parse_link_input",
        lambda _text: {
            "url": "https://example.com/agent",
            "tags": ["plan"],
            "category": "",
            "notes": "fresh note",
        },
    )
    monkeypatch.setattr(link_module, "validate_url", lambda _url: (True, ""))
    monkeypatch.setattr(link_module, "validate_tags", lambda _tags: (True, ""))

    update = _DummyUpdate(text="https://example.com/agent")
    await link_module.handle_link(update, _DummyContext())

    assert sheets.append_note_calls == [("5", "fresh note")]
    assert sheets.merge_keyword_calls == [("5", ["plan"])]
    assert "Link already exists!" in update.message.replies[0]["text"]


@pytest.mark.asyncio
async def test_link_tiktok_seeds_keywords_from_metadata_hints(monkeypatch):
    sheets = _LinkSheets()
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    monkeypatch.setattr(
        link_module,
        "parse_link_input",
        lambda _text: {
            "url": "https://www.tiktok.com/@creator/video/123456",
            "tags": ["custom"],
            "category": "",
            "notes": "",
        },
    )
    monkeypatch.setattr(link_module, "validate_url", lambda _url: (True, ""))
    monkeypatch.setattr(link_module, "validate_tags", lambda _tags: (True, ""))
    monkeypatch.setattr(link_module, "sanitize_html", lambda value: value)
    monkeypatch.setattr(link_module.gemini, "summarize", lambda _t, _d, _u: "AI summary")
    monkeypatch.setattr(
        link_module.scraper,
        "fetch_metadata",
        lambda _url: {
            "title": "Creator on TikTok",
            "description": "Meal prep tips #mealprep #keto",
            "thumbnail": "thumb.png",
            "source": "TikTok",
            "success": True,
            "error": None,
            "keywords_hint": ["mealprep", "keto", "creator"],
        },
    )

    captured = {}

    def _fake_detect_keywords(**kwargs):
        captured["manual_keywords"] = kwargs["manual_keywords"]
        return ["custom", "mealprep", "keto"]

    monkeypatch.setattr(link_module, "detect_keywords", _fake_detect_keywords)

    update = _DummyUpdate(text="https://www.tiktok.com/@creator/video/123456")
    await link_module.handle_link(update, _DummyContext())

    assert captured["manual_keywords"] == ["custom", "mealprep", "keto", "creator"]
    assert sheets.append_kwargs["tags"] == ["custom", "mealprep", "keto"]


@pytest.mark.asyncio
async def test_manage_edit_category_moves_record_to_new_topic(monkeypatch):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    await manage_module.edit_cmd(update, _DummyContext(args=["15", "category", "AI Agent"]))

    assert sheets.move_calls == [(15, "AI Agent")]
    assert "category: → AI Agent" in update.message.replies[0]["text"]


@pytest.mark.asyncio
async def test_callback_delete_uses_logical_id(monkeypatch):
    sheets = _CallbackSheets()
    callback_module = _load_handler_module(monkeypatch, "bot.handlers.callback", sheets)
    monkeypatch.setattr(callback_module, "_get_lang", lambda _query: "en")

    update = _DummyCallbackUpdate("c:del:7:y")
    await callback_module.handle_callback(update, _DummyContext())

    assert update.callback_query.answer_calls == 1
    assert sheets.deleted == [7]
    assert "Deleted!" in update.callback_query.edits[0]["text"]


@pytest.mark.asyncio
async def test_callback_edit_starts_pending_mode(monkeypatch):
    sheets = _CallbackSheets()
    callback_module = _load_handler_module(monkeypatch, "bot.handlers.callback", sheets)
    monkeypatch.setattr(callback_module, "_get_lang", lambda _query: "en")

    context = _DummyContext(user_data={})
    update = _DummyCallbackUpdate("e:set:7:title")
    await callback_module.handle_callback(update, context)

    assert context.user_data["pending_edit"] == {"row_id": 7, "field": "title"}
    assert "Send a new value for Title" in update.callback_query.edits[0]["text"]


@pytest.mark.asyncio
async def test_link_handler_applies_pending_edit_before_url_flow(monkeypatch):
    sheets = _LinkSheets()
    sheets.records["9"] = {"ID": "9", "Tieu de": "Old title", "Tags": "skill"}
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    update = _DummyUpdate(text="New title from interactive edit")
    context = _DummyContext(user_data={"pending_edit": {"row_id": 9, "field": "title"}})
    await link_module.handle_link(update, context)

    assert sheets.update_calls == [(9, 3, "New title from interactive edit")]
    assert context.user_data == {}
    assert "Updated!" in update.message.replies[0]["text"]
