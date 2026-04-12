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
    def __init__(self, title: str, records=None, raise_on_update: bool = False):
        self.title = title
        self._records = list(records or [])
        self.raise_on_update = raise_on_update
        self.clear_calls = 0
        self.update_calls = []
        self.delete_rows_calls = []
        self.operation_log = []

    def get_all_records(self):
        return list(self._records)

    def clear(self):
        self.clear_calls += 1
        self.operation_log.append("clear")
        self._records = []

    def update(self, *, range_name: str, values: list[list], value_input_option: str):
        self.operation_log.append("update")
        self.update_calls.append(
            {
                "range_name": range_name,
                "values": values,
                "value_input_option": value_input_option,
            }
        )
        if self.raise_on_update:
            raise RuntimeError("mirror update failed")
        if not values:
            self._records = []
            return

        headers = list(values[0])
        self._records = []
        for row in values[1:]:
            padded = list(row) + [""] * (len(headers) - len(row))
            self._records.append(dict(zip(headers, padded)))

    def delete_rows(self, start_index: int, end_index: int | None = None):
        if end_index is None:
            end_index = start_index
        self.operation_log.append("delete_rows")
        self.delete_rows_calls.append(
            {"start_index": start_index, "end_index": end_index}
        )
        start = max(start_index - 2, 0)
        end = max(end_index - 1, 0)
        del self._records[start:end]


class _FakeSheetsService:
    def __init__(
        self,
        records,
        mirror_records=None,
        mirror_raise_on_update: bool = False,
    ):
        self.records = list(records)
        self.mirror = _FakeMirrorSheet(
            "LIB_utils",
            records=mirror_records or [],
            raise_on_update=mirror_raise_on_update,
        )
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
        self.mirror.title = f"LIB_{group}"
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
async def test_lib_utils_group_includes_blank_or_invalid_rows(monkeypatch):
    _setup_lang(monkeypatch, "en")
    sheets = _FakeSheetsService(
        [
            {"ID": "1", "Library Group": "utils", "Tieu de": "Tooling", "Nguon": "example.com"},
            {"ID": "2", "Library Group": "", "Tieu de": "Legacy Blank", "Nguon": "example.com"},
            {"ID": "3", "Library Group": "legacy", "Tieu de": "Legacy Invalid", "Nguon": "example.com"},
            {"ID": "4", "Library Group": "icons", "Tieu de": "Lucide", "Nguon": "lucide.dev"},
        ]
    )
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=["utils"]))

    text = update.message.replies[0]["text"]
    assert "Group: utils" in text
    assert "Found <b>3</b> results" in text
    assert "<code>#1</code> Tooling" in text
    assert "<code>#2</code> Legacy Blank" in text
    assert "<code>#3</code> Legacy Invalid" in text


@pytest.mark.asyncio
async def test_lib_sheet_utils_backfills_blank_group_rows(monkeypatch):
    _setup_lang(monkeypatch, "en")
    sheets = _FakeSheetsService(
        [
            {"ID": "1", "Library Group": "", "Tieu de": "Blank Group"},
            {"ID": "2", "Library Group": "utils", "Tieu de": "Utils Group"},
            {"ID": "3", "Library Group": "icons", "Tieu de": "Icon Group"},
        ]
    )
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=["sheet", "utils"]))

    text = update.message.replies[0]["text"]
    assert sheets.ensure_calls == ["utils"]
    assert sheets.mirror.clear_calls == 0
    assert len(sheets.mirror.update_calls) == 1
    assert sheets.mirror.delete_rows_calls == []
    assert sheets.mirror.operation_log == ["update"]
    values = sheets.mirror.update_calls[0]["values"]
    assert [row[0] for row in values[1:]] == ["1", "2"]
    group_col = lib_module.SHEET_HEADERS.index("Library Group")
    assert [row[group_col] for row in values[1:]] == ["utils", "utils"]
    assert "Backfill: 2 | Cleanup: 0" in text


@pytest.mark.asyncio
async def test_lib_sheet_ensures_mirror_backfills_and_reports_cleanup(monkeypatch):
    _setup_lang(monkeypatch, "en")
    sheets = _FakeSheetsService(
        [
            {"ID": "1", "Library Group": "shadcn", "Tieu de": "Button"},
            {"ID": "2", "Library Group": "shadcn", "Tieu de": "Card"},
            {"ID": "3", "Library Group": "icons", "Tieu de": "Lucide"},
        ],
        mirror_records=[{"ID": "1"}, {"ID": "99"}, {"ID": "100"}],
    )
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    await lib_module.lib_cmd(update, _DummyContext(args=["sheet", "shadcn"]))

    text = update.message.replies[0]["text"]
    assert sheets.ensure_calls == ["shadcn"]
    assert sheets.mirror.clear_calls == 0
    assert len(sheets.mirror.update_calls) == 1
    assert sheets.mirror.delete_rows_calls == [{"start_index": 4, "end_index": 4}]
    assert sheets.mirror.operation_log == ["update", "delete_rows"]
    values = sheets.mirror.update_calls[0]["values"]
    assert [row[0] for row in values[1:]] == ["1", "2"]
    assert "Synced sheet LIB_shadcn" in text
    assert "Backfill: 2 | Cleanup: 2" in text


@pytest.mark.asyncio
async def test_lib_sheet_update_failure_keeps_existing_mirror_rows(monkeypatch):
    _setup_lang(monkeypatch, "en")
    existing_records = [{"ID": "1", "Library Group": "shadcn", "Tieu de": "Existing"}]
    sheets = _FakeSheetsService(
        [
            {"ID": "1", "Library Group": "shadcn", "Tieu de": "Button"},
            {"ID": "2", "Library Group": "shadcn", "Tieu de": "Card"},
        ],
        mirror_records=[dict(record) for record in existing_records],
        mirror_raise_on_update=True,
    )
    _setup_sheets(monkeypatch, sheets)
    update = _DummyUpdate()

    with pytest.raises(RuntimeError, match="mirror update failed"):
        await lib_module.lib_cmd(update, _DummyContext(args=["sheet", "shadcn"]))

    assert sheets.mirror.clear_calls == 0
    assert sheets.mirror.operation_log == ["update"]
    assert sheets.mirror.get_all_records() == existing_records


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
