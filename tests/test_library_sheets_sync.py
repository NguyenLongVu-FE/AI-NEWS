import gspread
from gspread.utils import ValueInputOption, rowcol_to_a1

from bot.config import SHEET_HEADERS, SHEET_DISPLAY_HEADERS
from bot.services.sheets import SheetsService

LEGACY_SHEET_HEADERS = [header for header in SHEET_HEADERS if header != "Library Group"]


class _FakeCell:
    def __init__(self, value=""):
        self.value = value


class _FakeWorksheet:
    def __init__(self, title: str, headers=None, rows=None):
        self.title = title
        self.headers = list(headers or [])
        self.data_rows = [list(row) for row in (rows or [])]
        self.update_calls = []
        self.appended_rows = []
        self.updated_cells = []
        self.deleted_rows = []

    def acell(self, _label: str):
        value = self.headers[0] if self.headers else ""
        return _FakeCell(value)

    def row_values(self, row: int):
        if row == 1:
            return list(self.headers)
        index = row - 2
        if 0 <= index < len(self.data_rows):
            return list(self.data_rows[index])
        return []

    def col_values(self, col: int):
        values = []
        if self.headers:
            values.append(self.headers[col - 1] if col - 1 < len(self.headers) else "")
        for row in self.data_rows:
            values.append(row[col - 1] if col - 1 < len(row) else "")
        return values

    def update(self, range_name=None, values=None, value_input_option=None):
        self.update_calls.append((range_name, values, value_input_option))
        if not values:
            return

        start_ref = (range_name or "A1").split(":")[0]
        row_digits = "".join(char for char in start_ref if char.isdigit())
        row_number = int(row_digits) if row_digits else 1

        if row_number == 1:
            self.headers = list(values[0])
            return

        index = row_number - 2
        while len(self.data_rows) <= index:
            self.data_rows.append([])
        self.data_rows[index] = list(values[0])

    def append_row(self, row, value_input_option=None):
        row = list(row)
        self.appended_rows.append((row, value_input_option))
        self.data_rows.append(row)

    def update_cell(self, row: int, col: int, value: str):
        self.updated_cells.append((row, col, value))
        if row == 1:
            while len(self.headers) < col:
                self.headers.append("")
            self.headers[col - 1] = value
            return

        index = row - 2
        while len(self.data_rows) <= index:
            self.data_rows.append([])
        while len(self.data_rows[index]) < col:
            self.data_rows[index].append("")
        self.data_rows[index][col - 1] = value

    def delete_rows(self, row: int):
        self.deleted_rows.append(row)
        index = row - 2
        if 0 <= index < len(self.data_rows):
            self.data_rows.pop(index)

    def get_all_records(self):
        records = []
        for row in self.data_rows:
            record = {}
            for index, header in enumerate(self.headers):
                record[header] = row[index] if index < len(row) else ""
            records.append(record)
        return records


class _FakeSpreadsheet:
    def __init__(self, sheet1: _FakeWorksheet):
        self.sheet1 = sheet1
        self._worksheets = {sheet1.title: sheet1}
        self.add_calls = []

    def worksheet(self, name: str):
        if name in self._worksheets:
            return self._worksheets[name]
        raise gspread.WorksheetNotFound(name)

    def add_worksheet(self, title: str, rows: int, cols: int):
        ws = _FakeWorksheet(title=title)
        self._worksheets[title] = ws
        self.add_calls.append((title, rows, cols))
        return ws


def _make_service(headers=None, rows=None):
    main_sheet = _FakeWorksheet(
        "Sheet1", headers=headers or SHEET_DISPLAY_HEADERS, rows=rows
    )
    spreadsheet = _FakeSpreadsheet(main_sheet)
    service = SheetsService.__new__(SheetsService)
    service.spreadsheet = spreadsheet
    return service, main_sheet, spreadsheet


def test_sheet_headers_include_library_group_between_thumbnail_and_reminder():
    thumbnail_index = SHEET_HEADERS.index("Thumbnail")
    assert SHEET_HEADERS[thumbnail_index + 1] == "Library Group"
    assert SHEET_HEADERS[thumbnail_index + 2] == "Nhac nho"


def test_ensure_headers_uses_range_for_current_header_count():
    service, main_sheet, _ = _make_service(headers=["ID"])
    service._ensure_headers()

    expected_range = f"A1:{rowcol_to_a1(1, len(SHEET_HEADERS))}"
    assert main_sheet.update_calls[0][0] == expected_range
    assert main_sheet.headers == SHEET_DISPLAY_HEADERS


def test_ensure_headers_migrates_legacy_layout_and_preserves_reminder_values():
    service, main_sheet, _ = _make_service(
        headers=LEGACY_SHEET_HEADERS,
        rows=[
            [
                "1",
                "2024-01-02 03:04:05",
                "Legacy row",
                "https://example.com",
                "example.com",
                "summary",
                "notes",
                "Tech",
                "legacy",
                "high",
                "chua_doc",
                "tester",
                "thumb.png",
                "2026-06-01",
            ]
        ],
    )

    service._ensure_headers()

    migrated_row = main_sheet.data_rows[0]
    assert main_sheet.headers == SHEET_DISPLAY_HEADERS
    assert migrated_row[SHEET_HEADERS.index("Library Group")] == ""
    assert migrated_row[SHEET_HEADERS.index("Nhac nho")] == "2026-06-01"


def test_append_link_defaults_library_group_to_utils():
    service, main_sheet, _ = _make_service()
    service.get_next_id = lambda: 10

    row_id = service.append_link(
        url="https://example.com",
        title="Example",
        source="example.com",
        ai_summary="Summary",
        notes="Notes",
        category="Tech",
        tags="docs",
        priority="high",
        status="chua_doc",
        user_name="tester",
        thumbnail="thumb.jpg",
    )

    saved_row, option = main_sheet.appended_rows[0]
    assert row_id == 10
    assert option == ValueInputOption.raw
    assert saved_row[SHEET_HEADERS.index("Library Group")] == "utils"
    assert saved_row[SHEET_HEADERS.index("Nhac nho")] == ""


def test_library_sheet_name_format():
    service = SheetsService.__new__(SheetsService)
    assert service._library_sheet_name("animation") == "LIB_animation"


def test_ensure_library_sheet_creates_and_reuses_mirror_sheet():
    service, _, spreadsheet = _make_service()

    created = service.ensure_library_sheet("animation")
    reused = service.ensure_library_sheet("animation")

    assert created is reused
    assert spreadsheet.add_calls == [("LIB_animation", 1000, len(SHEET_HEADERS))]
    assert created.headers == SHEET_DISPLAY_HEADERS
    assert created.update_calls[0][0] == f"A1:{rowcol_to_a1(1, len(SHEET_HEADERS))}"


def test_filter_by_library_group_is_case_insensitive():
    service = SheetsService.__new__(SheetsService)
    service.get_all_records = lambda: [
        {"ID": "1", "Library Group": "shadcn"},
        {"ID": "2", "Library Group": "icons"},
        {"ID": "3", "Library Group": "ShAdCn"},
    ]

    result = service.filter_by_library_group("SHADCN")
    assert [record["ID"] for record in result] == ["1", "3"]


def test_upsert_library_row_appends_then_updates_existing_row():
    service, _, _ = _make_service()

    service.upsert_library_row({"ID": "42", "Library Group": "animation", "Tieu de": "First"})
    mirror_sheet = service.ensure_library_sheet("animation")
    assert len(mirror_sheet.data_rows) == 1
    assert mirror_sheet.data_rows[0][SHEET_HEADERS.index("Tieu de")] == "First"

    service.upsert_library_row(
        {"ID": "42", "Library Group": "animation", "Tieu de": "Updated"}
    )
    assert len(mirror_sheet.data_rows) == 1
    assert mirror_sheet.data_rows[0][SHEET_HEADERS.index("Tieu de")] == "Updated"
    assert any(
        call[0] == f"A2:{rowcol_to_a1(2, len(SHEET_HEADERS))}"
        for call in mirror_sheet.update_calls
    )


def test_upsert_library_row_blank_group_routes_to_utils_mirror():
    service, _, spreadsheet = _make_service()

    service.upsert_library_row({"ID": "77", "Library Group": "   ", "Tieu de": "Utility"})

    assert spreadsheet.add_calls == [("LIB_utils", 1000, len(SHEET_HEADERS))]
    mirror_sheet = spreadsheet._worksheets["LIB_utils"]
    assert len(mirror_sheet.data_rows) == 1
    assert mirror_sheet.data_rows[0][0] == "77"
    assert mirror_sheet.data_rows[0][SHEET_HEADERS.index("Library Group")] == "utils"


def test_remove_library_row_deletes_row_by_id():
    service, _, _ = _make_service()
    service.upsert_library_row({"ID": "1", "Library Group": "icons"})
    service.upsert_library_row({"ID": "2", "Library Group": "icons"})
    mirror_sheet = service.ensure_library_sheet("icons")

    service.remove_library_row("2", "icons")

    assert [row[0] for row in mirror_sheet.data_rows] == ["1"]


def test_remove_library_row_does_not_create_mirror_sheet_when_missing():
    service, _, spreadsheet = _make_service()

    service.remove_library_row("2", "icons")

    assert spreadsheet.add_calls == []
    assert "LIB_icons" not in spreadsheet._worksheets


def test_backfill_library_groups_updates_only_missing_entries():
    service, main_sheet, _ = _make_service()
    service.get_all_records = lambda: [
        {
            "ID": "1",
            "Link goc": "https://motion.dev/docs",
            "Tieu de": "Motion Docs",
            "Tom tat AI": "",
            "Library Group": "",
        },
        {
            "ID": "2",
            "Link goc": "https://lucide.dev",
            "Tieu de": "Lucide",
            "Tom tat AI": "",
            "Library Group": "icons",
        },
        {
            "ID": "3",
            "Link goc": "https://example.com",
            "Tieu de": "Misc",
            "Tom tat AI": "",
            "Library Group": "   ",
        },
    ]

    detect_calls = []

    def _detect(url: str, title: str, summary: str):
        detect_calls.append((url, title, summary))
        if "motion.dev" in url:
            return "animation"
        return None

    service.backfill_library_groups(_detect)

    group_col = SHEET_HEADERS.index("Library Group") + 1
    assert main_sheet.updated_cells == [
        (2, group_col, "animation"),
        (4, group_col, "utils"),
    ]
    assert detect_calls == [
        ("https://motion.dev/docs", "Motion Docs", ""),
        ("https://example.com", "Misc", ""),
    ]
