import gspread

from bot.config import SHEET_DISPLAY_HEADERS, SHEET_HEADERS, TOPIC_SHEET_PREFIX
from bot.services.sheets import SheetsService


class _FakeCell:
    def __init__(self, value=""):
        self.value = value


class _FakeWorksheet:
    _next_sheet_id = 1

    def __init__(self, title: str, headers=None, rows=None):
        self.title = title
        self.headers = list(headers or [])
        self.data_rows = [list(row) for row in (rows or [])]
        self.update_calls = []
        self.appended_rows = []
        self.deleted_rows = []
        self._properties = {"sheetId": _FakeWorksheet._next_sheet_id}
        _FakeWorksheet._next_sheet_id += 1

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

    def delete_rows(self, start_index: int, end_index: int | None = None):
        if end_index is None:
            end_index = start_index
        self.deleted_rows.append((start_index, end_index))
        start = max(start_index - 2, 0)
        end = max(end_index - 1, 0)
        del self.data_rows[start:end]

    def get_all_records(self):
        records = []
        for row in self.data_rows:
            padded = list(row) + [""] * (len(self.headers) - len(row))
            records.append(dict(zip(self.headers, padded)))
        return records

    def clear(self):
        self.headers = []
        self.data_rows = []

    def update_title(self, new_title: str):
        self.title = new_title

    def cell(self, row: int, col: int):
        if row == 1:
            value = self.headers[col - 1] if col - 1 < len(self.headers) else ""
            return _FakeCell(value)
        index = row - 2
        if 0 <= index < len(self.data_rows):
            value = self.data_rows[index][col - 1] if col - 1 < len(self.data_rows[index]) else ""
            return _FakeCell(value)
        return _FakeCell("")


class _FakeSpreadsheet:
    def __init__(self, worksheets):
        self._worksheets = list(worksheets)
        self.batch_requests = []
        self.deleted_titles = []
        self.add_calls = []

    def worksheets(self):
        return list(self._worksheets)

    def worksheet(self, name: str):
        for ws in self._worksheets:
            if ws.title == name:
                return ws
        raise gspread.WorksheetNotFound(name)

    def add_worksheet(self, title: str, rows: int, cols: int):
        ws = _FakeWorksheet(title=title)
        self._worksheets.append(ws)
        self.add_calls.append((title, rows, cols))
        return ws

    def del_worksheet(self, ws):
        self.deleted_titles.append(ws.title)
        self._worksheets = [item for item in self._worksheets if item is not ws]

    def batch_update(self, payload):
        self.batch_requests.append(payload)


def _make_service(worksheets):
    service = SheetsService.__new__(SheetsService)
    service.spreadsheet = _FakeSpreadsheet(worksheets)
    return service


def test_bootstrap_removes_legacy_data_sheets_and_keeps_settings():
    legacy_sheet = _FakeWorksheet("Sheet1", headers=SHEET_DISPLAY_HEADERS, rows=[["1"]])
    settings_sheet = _FakeWorksheet("Settings", headers=["user_id"], rows=[["100"]])
    service = _make_service([legacy_sheet, settings_sheet])

    service._bootstrap_topic_workspace()

    titles = [ws.title for ws in service.spreadsheet.worksheets()]
    assert "Settings" in titles
    assert "Sheet1" not in titles


def test_bootstrap_keeps_existing_dashboard_sheet():
    legacy_sheet = _FakeWorksheet("Sheet1", headers=SHEET_DISPLAY_HEADERS, rows=[["1"]])
    settings_sheet = _FakeWorksheet("Settings", headers=["user_id"], rows=[["100"]])
    dashboard_sheet = _FakeWorksheet("DASHBOARD", headers=["k"], rows=[["v"]])
    service = _make_service([legacy_sheet, settings_sheet, dashboard_sheet])

    service._bootstrap_topic_workspace()

    titles = [ws.title for ws in service.spreadsheet.worksheets()]
    assert "Settings" in titles
    assert "DASHBOARD" in titles
    assert "Sheet1" not in titles


def test_append_link_creates_topic_sheet_with_new_schema():
    service = _make_service([_FakeWorksheet("Settings", headers=["user_id"], rows=[])])

    row_id = service.append_link(
        url="https://example.com/agent",
        title="AI Agent plan",
        source="example.com",
        ai_summary="summary",
        notes="note",
        category="AI Agent",
        tags=["skill", "plan"],
        user_name="Tester",
        thumbnail="thumb.png",
    )

    assert row_id == 1
    topic_ws = service.spreadsheet.worksheet(f"{TOPIC_SHEET_PREFIX}ai-agent")
    assert topic_ws.headers == SHEET_DISPLAY_HEADERS
    assert topic_ws.data_rows[0][SHEET_HEADERS.index("Chu de")] == "AI Agent"
    assert topic_ws.data_rows[0][SHEET_HEADERS.index("Tags")] == "skill, plan"


def test_append_link_triggers_dashboard_rebuild():
    service = _make_service([_FakeWorksheet("Settings", headers=["user_id"], rows=[])])
    calls = []
    service._safe_rebuild_dashboard = lambda: calls.append("called")

    service.append_link(
        url="https://example.com/agent",
        title="AI Agent plan",
        source="example.com",
        ai_summary="summary",
        notes="note",
        category="AI Agent",
        tags=["skill", "plan"],
        user_name="Tester",
        thumbnail="thumb.png",
    )

    assert calls == ["called"]


def test_find_by_url_returns_logical_id_across_topic_sheets():
    ws_a = _FakeWorksheet(
        f"{TOPIC_SHEET_PREFIX}ai-agent",
        headers=SHEET_DISPLAY_HEADERS,
        rows=[["2", "", "", "https://example.com/a"]],
    )
    ws_b = _FakeWorksheet(
        f"{TOPIC_SHEET_PREFIX}fe",
        headers=SHEET_DISPLAY_HEADERS,
        rows=[["7", "", "", "https://example.com/b"]],
    )
    service = _make_service([ws_a, ws_b])

    assert service.find_by_url("https://example.com/b") == "7"


def test_merge_keywords_by_id_appends_unique_tokens():
    ws = _FakeWorksheet(
        f"{TOPIC_SHEET_PREFIX}ai-agent",
        headers=SHEET_DISPLAY_HEADERS,
        rows=[
            ["9", "", "Title", "https://example.com", "", "", "", "AI Agent", "skill", "", ""]
        ],
    )
    service = _make_service([ws])

    ok = service.merge_keywords_by_id(9, ["plan", "skill", "workflow"])

    assert ok is True
    assert ws.data_rows[0][SHEET_HEADERS.index("Tags")] == "skill, plan, workflow"


def test_move_row_to_new_topic_sheet():
    ws = _FakeWorksheet(
        f"{TOPIC_SHEET_PREFIX}tech",
        headers=SHEET_DISPLAY_HEADERS,
        rows=[
            ["5", "", "Title", "https://example.com", "", "", "", "Tech", "python", "", ""]
        ],
    )
    service = _make_service([ws])

    moved = service.move_row_to_topic_by_id(5, "AI Agent")

    assert moved is True
    old_ws = service.spreadsheet.worksheet(f"{TOPIC_SHEET_PREFIX}tech")
    new_ws = service.spreadsheet.worksheet(f"{TOPIC_SHEET_PREFIX}ai-agent")
    assert old_ws.data_rows == []
    assert new_ws.data_rows[0][SHEET_HEADERS.index("Chu de")] == "AI Agent"


def test_rebuild_dashboard_sheet_writes_topic_summary():
    ws_agent = _FakeWorksheet(
        f"{TOPIC_SHEET_PREFIX}ai-agent",
        headers=SHEET_DISPLAY_HEADERS,
        rows=[
            [
                "1",
                "2026-04-13 10:00:00",
                "Agent A",
                "https://example.com/a",
                "example.com",
                "summary",
                "",
                "AI Agent",
                "skill, plan",
                "Tester",
                "",
            ],
            [
                "2",
                "2026-04-10 09:00:00",
                "Agent B",
                "https://example.com/b",
                "example.com",
                "summary",
                "",
                "AI Agent",
                "plan",
                "Tester",
                "",
            ],
        ],
    )
    ws_fe = _FakeWorksheet(
        f"{TOPIC_SHEET_PREFIX}fe",
        headers=SHEET_DISPLAY_HEADERS,
        rows=[
            [
                "3",
                "2026-04-13 11:00:00",
                "FE C",
                "https://example.com/c",
                "example.com",
                "summary",
                "",
                "FE",
                "react",
                "Tester",
                "",
            ],
        ],
    )
    service = _make_service([ws_agent, ws_fe])

    service.rebuild_dashboard_sheet()

    dashboard = service.spreadsheet.worksheet("DASHBOARD")
    assert dashboard.update_calls
    values = dashboard.update_calls[-1][1]
    assert values[1][0] == "Tổng links"
    assert values[1][1] == 3
    assert values[2] == ["Tổng chủ đề", 2]
    assert values[5] == ["Chủ đề", "Sheet", "Tổng links", "Mới hôm nay", "Mới 7 ngày", "Top 5 từ khóa", "URL"]
    assert values[6][0] == "AI Agent"
    assert values[6][2] == 2
    assert "plan(2)" in values[6][5]
    assert "#gid=" in values[6][6]
