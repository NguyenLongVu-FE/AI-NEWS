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
    def __init__(self, upsert_raises: bool = False, existing_row: int | None = None):
        self.upsert_raises = upsert_raises
        self.existing_row = existing_row
        self.append_kwargs = None
        self.upsert_records = []
        self.append_note_calls = []
        self.get_row_calls = []
        self.get_row_by_id_calls = []
        self.existing_record = (
            {
                "ID": "15",
                "Library Group": "icons",
                "Tieu de": "Existing docs",
                "Nguoi luu": "Tester",
                "Ghi chu tay": "Old note",
            }
            if existing_row
            else None
        )

    def find_by_url(self, _url: str):
        return self.existing_row

    def append_link(self, **kwargs):
        self.append_kwargs = dict(kwargs)
        return 9

    def get_row(self, row: int):
        self.get_row_calls.append(row)
        if self.existing_row == row and self.existing_record:
            return dict(self.existing_record)
        return {"ID": "999", "Library Group": "wrong", "Tieu de": "Wrong row"}

    def get_row_by_id(self, row_id: int | str):
        self.get_row_by_id_calls.append(row_id)
        if self.existing_record and str(row_id) == str(self.existing_record.get("ID", "")):
            return dict(self.existing_record)
        return {
            "ID": str(row_id),
            "Library Group": self.append_kwargs.get("library_group", ""),
            "Tieu de": "Button docs",
        }

    def append_note(self, row: int, note: str):
        self.append_note_calls.append((row, note))
        if self.existing_row == row and self.existing_record is not None:
            current = self.existing_record.get("Ghi chu tay", "")
            separator = " | " if current else ""
            self.existing_record["Ghi chu tay"] = f"{current}{separator}{note}"

    def upsert_library_row(self, record: dict):
        self.upsert_records.append(dict(record))
        if self.upsert_raises:
            raise RuntimeError("mirror sync failed")


class _ManageSheets:
    def __init__(self, upsert_raises: bool = False):
        self.upsert_raises = upsert_raises
        self.update_cell_calls = []
        self.update_cell_by_id_calls = []
        self.append_note_calls = []
        self.append_note_by_id_calls = []
        self.remove_calls = []
        self.upsert_calls = []
        self.get_row_calls = []
        self.get_row_by_id_calls = []
        self.row_index_by_id = {15: 2}
        self.records_by_id = {
            15: {
                "ID": "15",
                "Library Group": "icons",
                "Tieu de": "Lucide",
                "Uu tien": "medium",
                "Trang thai": "chua_doc",
                "Ghi chu tay": "Existing note",
            }
        }
        self.records_by_row = {
            row_index: self.records_by_id[row_id]
            for row_id, row_index in self.row_index_by_id.items()
        }

    def get_row(self, row: int):
        self.get_row_calls.append(row)
        record = self.records_by_row.get(row)
        return dict(record) if record else None

    def get_row_by_id(self, row_id: int):
        self.get_row_by_id_calls.append(row_id)
        record = self.records_by_id.get(row_id)
        return dict(record) if record else None

    def update_cell(self, row: int, col: int, value: str):
        self.update_cell_calls.append((row, col, value))
        record = self.records_by_row.get(row)
        if record:
            record[SHEET_HEADERS[col - 1]] = value

    def update_cell_by_id(self, row_id: int, col: int, value: str):
        self.update_cell_by_id_calls.append((row_id, col, value))
        record = self.records_by_id.get(row_id)
        if not record:
            return False
        record[SHEET_HEADERS[col - 1]] = value
        return True

    def append_note(self, row: int, note: str):
        self.append_note_calls.append((row, note))
        record = self.records_by_row.get(row)
        if record is None:
            return
        current = record.get("Ghi chu tay", "")
        separator = " | " if current else ""
        record["Ghi chu tay"] = f"{current}{separator}{note}"

    def append_note_by_id(self, row_id: int, note: str):
        self.append_note_by_id_calls.append((row_id, note))
        row_index = self.row_index_by_id.get(row_id)
        if row_index is None:
            return False
        self.append_note(row_index, note)
        return True

    def remove_library_row(self, row_id: str, group: str):
        self.remove_calls.append((row_id, group))

    def upsert_library_row(self, record: dict):
        self.upsert_calls.append(dict(record))
        if self.upsert_raises:
            raise RuntimeError("mirror sync failed")


class _CallbackSheets:
    def __init__(self, upsert_raises: bool = False, remove_raises: bool = False):
        self.upsert_raises = upsert_raises
        self.remove_raises = remove_raises
        self.deleted_rows = []
        self.deleted_row_ids = []
        self.remove_calls = []
        self.update_cell_calls = []
        self.update_cell_by_id_calls = []
        self.upsert_calls = []
        self.get_row_calls = []
        self.get_row_by_id_calls = []
        self.records_by_id = {
            7: {
                "ID": "7",
                "Library Group": "icons",
                "Tieu de": "Icon docs",
                "Uu tien": "medium",
                "Trang thai": "chua_doc",
            }
        }

    def get_row(self, row: int):
        self.get_row_calls.append(row)
        record = self.records_by_id.get(row)
        return dict(record) if record else None

    def get_row_by_id(self, row_id: int):
        self.get_row_by_id_calls.append(row_id)
        record = self.records_by_id.get(row_id)
        return dict(record) if record else None

    def delete_row(self, row: int):
        self.deleted_rows.append(row)
        self.records_by_id.pop(row, None)

    def delete_row_by_id(self, row_id: int):
        self.deleted_row_ids.append(row_id)
        self.records_by_id.pop(row_id, None)
        return True

    def update_cell(self, row: int, col: int, value: str):
        self.update_cell_calls.append((row, col, value))
        record = self.records_by_id.get(row)
        if record:
            record[SHEET_HEADERS[col - 1]] = value

    def update_cell_by_id(self, row_id: int, col: int, value: str):
        self.update_cell_by_id_calls.append((row_id, col, value))
        record = self.records_by_id.get(row_id)
        if not record:
            return False
        record[SHEET_HEADERS[col - 1]] = value
        return True

    def remove_library_row(self, row_id: str, group: str):
        self.remove_calls.append((row_id, group))
        if self.remove_raises:
            raise RuntimeError("mirror cleanup failed")

    def upsert_library_row(self, record: dict):
        self.upsert_calls.append(dict(record))
        if self.upsert_raises:
            raise RuntimeError("mirror sync failed")


@pytest.mark.asyncio
async def test_link_save_sync_uses_override_and_mirror_upsert_is_non_blocking(
    monkeypatch, caplog
):
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
    with caplog.at_level("WARNING"):
        await link_module.handle_link(update, _DummyContext())

    assert sheets.append_kwargs["library_group"] == "shadcn"
    assert sheets.get_row_calls == []
    assert sheets.get_row_by_id_calls == [9]
    assert len(sheets.upsert_records) == 1
    assert update.message.editables[0].edits
    assert "Saved successfully!" in update.message.editables[0].edits[0]["text"]
    assert any(
        link_module.t("mirror_sync_warning", "en") in reply["text"]
        for reply in update.message.replies
    )
    assert "Mirror upsert failed for row_id=9" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("override_value", ["", "not-a-group"])
async def test_link_save_sync_falls_back_to_detect_when_override_missing_or_invalid(
    monkeypatch, override_value
):
    sheets = _LinkSheets()
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    monkeypatch.setattr(
        link_module,
        "parse_link_input",
        lambda _text: {
            "url": "https://example.com/icons",
            "tags": [],
            "priority": "medium",
            "category": "Other",
            "notes": "",
            "library_group_override": override_value,
        },
    )
    monkeypatch.setattr(link_module, "validate_url", lambda _url: (True, ""))
    monkeypatch.setattr(link_module, "validate_tags", lambda _tags: (True, ""))
    monkeypatch.setattr(link_module, "sanitize_html", lambda value: value)
    monkeypatch.setattr(
        link_module.scraper,
        "fetch_metadata",
        lambda _url: {
            "title": "Icon docs",
            "description": "docs",
            "thumbnail": "thumb.png",
            "source": "example.com",
            "success": True,
            "error": None,
        },
    )
    monkeypatch.setattr(link_module.gemini, "summarize", lambda *_args: "summary")

    detect_calls = []

    def _detect(url: str, title: str, summary: str):
        detect_calls.append((url, title, summary))
        return "icons"

    monkeypatch.setattr(link_module, "detect_library_group", _detect)

    update = _DummyUpdate(text="https://example.com/icons")
    await link_module.handle_link(update, _DummyContext())

    assert detect_calls == [("https://example.com/icons", "Icon docs", "summary")]
    assert sheets.append_kwargs["library_group"] == "icons"
    assert sheets.get_row_by_id_calls == [9]


@pytest.mark.asyncio
async def test_link_existing_url_note_merge_syncs_mirror(monkeypatch):
    sheets = _LinkSheets(existing_row=2)
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    monkeypatch.setattr(
        link_module,
        "parse_link_input",
        lambda _text: {
            "url": "https://example.com/icons",
            "tags": [],
            "priority": "medium",
            "category": "Other",
            "notes": "fresh note",
            "library_group_override": "",
        },
    )
    monkeypatch.setattr(link_module, "validate_url", lambda _url: (True, ""))
    monkeypatch.setattr(link_module, "validate_tags", lambda _tags: (True, ""))

    update = _DummyUpdate(text="https://example.com/icons fresh note")
    await link_module.handle_link(update, _DummyContext())

    assert sheets.append_note_calls == [(2, "fresh note")]
    assert sheets.get_row_calls == [2]
    assert sheets.get_row_by_id_calls == ["15"]
    assert len(sheets.upsert_records) == 1
    assert "fresh note" in sheets.upsert_records[0]["Ghi chu tay"]
    assert update.message.replies
    assert link_module.t("notes_merged", "en") in update.message.replies[0]["text"]
    assert (
        link_module.t("mirror_sync_warning", "en")
        not in update.message.replies[0]["text"]
    )


@pytest.mark.asyncio
async def test_link_existing_url_note_merge_warns_when_mirror_sync_fails(
    monkeypatch, caplog
):
    sheets = _LinkSheets(upsert_raises=True, existing_row=2)
    link_module = _load_handler_module(monkeypatch, "bot.handlers.link", sheets)

    monkeypatch.setattr(
        link_module,
        "parse_link_input",
        lambda _text: {
            "url": "https://example.com/icons",
            "tags": [],
            "priority": "medium",
            "category": "Other",
            "notes": "fresh note",
            "library_group_override": "",
        },
    )
    monkeypatch.setattr(link_module, "validate_url", lambda _url: (True, ""))
    monkeypatch.setattr(link_module, "validate_tags", lambda _tags: (True, ""))

    update = _DummyUpdate(text="https://example.com/icons fresh note")
    with caplog.at_level("WARNING"):
        await link_module.handle_link(update, _DummyContext())

    assert sheets.append_note_calls == [(2, "fresh note")]
    assert sheets.get_row_by_id_calls == ["15"]
    assert len(sheets.upsert_records) == 1
    assert link_module.t("mirror_sync_warning", "en") in update.message.replies[0]["text"]
    assert "Mirror upsert failed for row_id=15" in caplog.text


@pytest.mark.asyncio
async def test_edit_library_group_moves_between_mirror_sheets(monkeypatch):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    context = _DummyContext(args=["15", "library_group", "ShAdCn"])
    await manage_module.edit_cmd(update, context)

    group_col = SHEET_HEADERS.index("Library Group") + 1
    assert sheets.get_row_calls == []
    assert sheets.get_row_by_id_calls == [15, 15]
    assert sheets.update_cell_calls == []
    assert sheets.update_cell_by_id_calls == [(15, group_col, "shadcn")]
    assert sheets.remove_calls == [("15", "icons")]
    assert len(sheets.upsert_calls) == 1
    assert sheets.upsert_calls[0]["Library Group"] == "shadcn"
    assert "library_group: → shadcn" in update.message.replies[0]["text"]


@pytest.mark.asyncio
async def test_edit_non_library_field_syncs_mirror_row(monkeypatch):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    context = _DummyContext(args=["15", "title", "New Lucide"])
    await manage_module.edit_cmd(update, context)

    title_col = SHEET_HEADERS.index("Tieu de") + 1
    assert sheets.get_row_by_id_calls == [15, 15]
    assert sheets.update_cell_by_id_calls == [(15, title_col, "New Lucide")]
    assert sheets.remove_calls == []
    assert len(sheets.upsert_calls) == 1
    assert sheets.upsert_calls[0]["Tieu de"] == "New Lucide"
    assert "title: → New Lucide" in update.message.replies[0]["text"]


@pytest.mark.asyncio
async def test_note_command_syncs_mirror_after_append(monkeypatch):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    await manage_module.note_cmd(update, _DummyContext(args=["15", "Need", "examples"]))

    assert sheets.get_row_calls == []
    assert sheets.get_row_by_id_calls == [15, 15]
    assert sheets.append_note_by_id_calls == [(15, "Need examples")]
    assert sheets.append_note_calls == [(2, "Need examples")]
    assert len(sheets.upsert_calls) == 1
    assert "Need examples" in sheets.upsert_calls[0]["Ghi chu tay"]
    assert manage_module.t("mirror_sync_warning", "en") not in update.message.replies[0]["text"]


@pytest.mark.asyncio
async def test_note_command_warns_when_mirror_sync_fails(monkeypatch, caplog):
    sheets = _ManageSheets(upsert_raises=True)
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    with caplog.at_level("WARNING"):
        await manage_module.note_cmd(update, _DummyContext(args=["15", "Need", "examples"]))

    assert sheets.get_row_calls == []
    assert sheets.get_row_by_id_calls == [15, 15]
    assert sheets.append_note_by_id_calls == [(15, "Need examples")]
    assert sheets.append_note_calls == [(2, "Need examples")]
    assert len(sheets.upsert_calls) == 1
    assert manage_module.t("mirror_sync_warning", "en") in update.message.replies[0]["text"]
    assert "Mirror upsert failed for row_id=15" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command_name", "args", "column", "field_name", "expected_value"),
    [
        ("status_cmd", ["15", "dang_doc"], 11, "Trang thai", "dang_doc"),
        ("priority_cmd", ["15", "high"], 10, "Uu tien", "high"),
    ],
)
async def test_status_and_priority_commands_sync_mirror(
    monkeypatch, command_name, args, column, field_name, expected_value
):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    command = getattr(manage_module, command_name)
    await command(update, _DummyContext(args=args))

    assert sheets.update_cell_by_id_calls == [(15, column, expected_value)]
    assert len(sheets.upsert_calls) == 1
    assert sheets.upsert_calls[0][field_name] == expected_value


@pytest.mark.asyncio
async def test_view_command_uses_logical_id_lookup(monkeypatch):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    await manage_module.view_cmd(update, _DummyContext(args=["15"]))

    assert sheets.get_row_calls == []
    assert sheets.get_row_by_id_calls == [15]
    assert update.message.replies
    assert "Lucide" in update.message.replies[0]["text"]


@pytest.mark.asyncio
async def test_delete_command_confirmation_uses_logical_id_lookup(monkeypatch):
    sheets = _ManageSheets()
    manage_module = _load_handler_module(monkeypatch, "bot.handlers.manage", sheets)

    update = _DummyUpdate()
    await manage_module.delete_cmd(update, _DummyContext(args=["15"]))

    assert sheets.get_row_calls == []
    assert sheets.get_row_by_id_calls == [15]
    assert update.message.replies
    reply = update.message.replies[0]
    assert "Lucide" in reply["text"]
    keyboard = reply["kwargs"]["reply_markup"]
    assert keyboard.inline_keyboard[0][0].callback_data == "c:del:15:y"
    assert keyboard.inline_keyboard[0][1].callback_data == "v:15"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_data", "column", "field_name", "expected_value"),
    [
        ("s:status:7:dang_doc", 11, "Trang thai", "dang_doc"),
        ("s:priority:7:high", 10, "Uu tien", "high"),
    ],
)
async def test_callback_status_and_priority_sync_mirror(
    monkeypatch, callback_data, column, field_name, expected_value
):
    sheets = _CallbackSheets()
    callback_module = _load_handler_module(monkeypatch, "bot.handlers.callback", sheets)
    monkeypatch.setattr(callback_module, "_get_lang", lambda _query: "en")

    update = _DummyCallbackUpdate(callback_data)
    await callback_module.handle_callback(update, _DummyContext())

    assert update.callback_query.answer_calls == 1
    assert sheets.update_cell_by_id_calls == [(7, column, expected_value)]
    assert len(sheets.upsert_calls) == 1
    assert sheets.upsert_calls[0][field_name] == expected_value


@pytest.mark.asyncio
async def test_callback_update_warns_when_mirror_sync_fails(monkeypatch, caplog):
    sheets = _CallbackSheets(upsert_raises=True)
    callback_module = _load_handler_module(monkeypatch, "bot.handlers.callback", sheets)
    monkeypatch.setattr(callback_module, "_get_lang", lambda _query: "en")

    update = _DummyCallbackUpdate("s:status:7:dang_doc")
    with caplog.at_level("WARNING"):
        await callback_module.handle_callback(update, _DummyContext())

    assert update.callback_query.answer_calls == 1
    assert sheets.update_cell_by_id_calls == [(7, 11, "dang_doc")]
    assert callback_module.t("mirror_sync_warning", "en") in update.callback_query.edits[-1]["text"]
    assert "Mirror upsert failed for row_id=7" in caplog.text


@pytest.mark.asyncio
async def test_delete_callback_removes_mirror_row(monkeypatch):
    sheets = _CallbackSheets()
    callback_module = _load_handler_module(monkeypatch, "bot.handlers.callback", sheets)
    monkeypatch.setattr(callback_module, "_get_lang", lambda _query: "en")

    update = _DummyCallbackUpdate("c:del:7:y")
    await callback_module.handle_callback(update, _DummyContext())

    assert update.callback_query.answer_calls == 1
    assert sheets.get_row_calls == []
    assert sheets.get_row_by_id_calls == [7]
    assert sheets.deleted_rows == []
    assert sheets.deleted_row_ids == [7]
    assert sheets.remove_calls == [("7", "icons")]
    assert update.callback_query.edits
    assert "Deleted!" in update.callback_query.edits[0]["text"]


@pytest.mark.asyncio
async def test_delete_callback_warns_when_mirror_cleanup_fails(monkeypatch, caplog):
    sheets = _CallbackSheets(remove_raises=True)
    callback_module = _load_handler_module(monkeypatch, "bot.handlers.callback", sheets)
    monkeypatch.setattr(callback_module, "_get_lang", lambda _query: "en")

    update = _DummyCallbackUpdate("c:del:7:y")
    with caplog.at_level("WARNING"):
        await callback_module.handle_callback(update, _DummyContext())

    assert update.callback_query.answer_calls == 1
    assert sheets.deleted_row_ids == [7]
    assert sheets.remove_calls == [("7", "icons")]
    assert update.callback_query.edits
    assert "Deleted!" in update.callback_query.edits[0]["text"]
    assert callback_module.t("mirror_sync_warning", "en") in update.callback_query.edits[0]["text"]
    assert "Mirror cleanup failed for deleted row_id=7 in group=icons" in caplog.text
