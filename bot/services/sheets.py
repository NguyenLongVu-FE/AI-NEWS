from datetime import datetime

import gspread
from gspread.utils import ValueInputOption, rowcol_to_a1

from bot.config import GOOGLE_SHEET_ID, SHEET_HEADERS, get_google_credentials


_instance = None


def get_sheets_service() -> "SheetsService":
    global _instance
    if _instance is None:
        _instance = SheetsService()
    return _instance


class SheetsService:
    def __init__(self):
        credentials = get_google_credentials()
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        self.gc = gspread.service_account_from_dict(credentials, scopes=scopes)
        self.spreadsheet = self.gc.open_by_key(GOOGLE_SHEET_ID)
        self._ensure_headers()

    def _ensure_headers(self):
        ws = self.spreadsheet.sheet1
        current_headers = ws.row_values(1)
        legacy_headers = [
            header for header in SHEET_HEADERS if header != "Library Group"
        ]

        if current_headers == legacy_headers:
            self._migrate_legacy_headers(ws)
            return

        if current_headers != SHEET_HEADERS:
            ws.update(
                range_name=self._sheet_header_range(),
                values=[SHEET_HEADERS],
                value_input_option="RAW",
            )

    def _migrate_legacy_headers(self, ws):
        legacy_records = ws.get_all_records()
        ws.update(
            range_name=self._sheet_header_range(),
            values=[SHEET_HEADERS],
            value_input_option="RAW",
        )

        for row_index, record in enumerate(legacy_records, start=2):
            migrated_row = [record.get(header, "") for header in SHEET_HEADERS]
            ws.update(
                range_name=f"A{row_index}:{rowcol_to_a1(row_index, len(SHEET_HEADERS))}",
                values=[migrated_row],
                value_input_option="RAW",
            )

    @staticmethod
    def _sheet_header_range() -> str:
        return f"A1:{rowcol_to_a1(1, len(SHEET_HEADERS))}"

    def _get_worksheet(self):
        return self.spreadsheet.sheet1

    def get_next_id(self):
        ws = self._get_worksheet()
        ids = ws.col_values(1)
        if len(ids) <= 1:
            return 1
        try:
            return int(ids[-1]) + 1
        except (ValueError, IndexError):
            return 1

    def find_by_url(self, url: str):
        ws = self._get_worksheet()
        urls = ws.col_values(4)
        for i, u in enumerate(urls):
            if u == url:
                return i + 1
        return None

    def append_link(
        self,
        url: str,
        title: str,
        source: str,
        ai_summary: str,
        notes: str,
        category: str,
        tags: str,
        priority: str,
        status: str,
        user_name: str,
        thumbnail: str,
        reminder_date: str = "",
        library_group: str = "utils",
    ):
        ws = self._get_worksheet()
        row_id = self.get_next_id()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        normalized_group = str(library_group or "utils").strip().lower() or "utils"
        row = [
            row_id,
            now,
            title,
            url,
            source,
            ai_summary,
            notes,
            category,
            tags,
            priority,
            status,
            user_name,
            thumbnail,
            normalized_group,
            reminder_date,
        ]
        ws.append_row(row, value_input_option=ValueInputOption.raw)
        return row_id

    def _library_sheet_name(self, group: str) -> str:
        key = str(group or "").strip().lower() or "utils"
        return f"LIB_{key}"

    def ensure_library_sheet(self, group: str):
        ws = self._get_library_sheet(group)
        if ws is not None:
            return ws

        name = self._library_sheet_name(group)
        ws = self.spreadsheet.add_worksheet(
            title=name,
            rows=1000,
            cols=len(SHEET_HEADERS),
        )
        ws.update(
            range_name=self._sheet_header_range(),
            values=[SHEET_HEADERS],
            value_input_option="RAW",
        )
        return ws

    def _get_library_sheet(self, group: str):
        name = self._library_sheet_name(group)
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            return None

    def filter_by_library_group(self, group: str):
        group_key = str(group or "").strip().lower()
        if not group_key:
            return []
        return [
            record
            for record in self.get_all_records()
            if str(record.get("Library Group", "")).strip().lower() == group_key
        ]

    def upsert_library_row(self, record: dict):
        group = str(record.get("Library Group", "")).strip().lower()
        if not group:
            return

        row_id = str(record.get("ID", "")).strip()
        if not row_id:
            return

        ws = self.ensure_library_sheet(group)
        ids = ws.col_values(1)
        row = [record.get(header, "") for header in SHEET_HEADERS]

        if row_id in ids:
            row_number = ids.index(row_id) + 1
            ws.update(
                range_name=f"A{row_number}:{rowcol_to_a1(row_number, len(SHEET_HEADERS))}",
                values=[row],
                value_input_option="RAW",
            )
            return

        ws.append_row(row, value_input_option=ValueInputOption.raw)

    def remove_library_row(self, row_id: str, group: str):
        group_key = str(group or "").strip().lower()
        row_key = str(row_id or "").strip()
        if not group_key or not row_key:
            return

        ws = self._get_library_sheet(group_key)
        if ws is None:
            return

        ids = ws.col_values(1)
        if row_key in ids:
            row_number = ids.index(row_key) + 1
            if row_number > 1:
                ws.delete_rows(row_number)

    def backfill_library_groups(self, detect_group_fn):
        ws = self._get_worksheet()
        group_col = SHEET_HEADERS.index("Library Group") + 1
        records = self.get_all_records()

        for idx, record in enumerate(records, start=2):
            existing_group = str(record.get("Library Group", "")).strip()
            if existing_group:
                continue

            detected_group = detect_group_fn(
                str(record.get("Link goc", "")),
                str(record.get("Tieu de", "")),
                str(record.get("Tom tat AI", "")),
            )
            group = str(detected_group or "utils").strip().lower() or "utils"
            ws.update_cell(idx, group_col, group)

    def update_cell(self, row: int, col: int, value: str):
        ws = self._get_worksheet()
        ws.update_cell(row, col, value)

    def append_note(self, row: int, note: str):
        ws = self._get_worksheet()
        current = ws.cell(row, 7).value or ""
        separator = " | " if current else ""
        ws.update_cell(row, 7, f"{current}{separator}{note}")

    def get_all_records(self):
        ws = self._get_worksheet()
        return ws.get_all_records()

    def delete_row(self, row: int):
        ws = self._get_worksheet()
        ws.delete_rows(row)

    def get_row(self, row: int):
        ws = self._get_worksheet()
        values = ws.row_values(row)
        if not values:
            return None
        keys = SHEET_HEADERS
        return dict(zip(keys, values + [""] * (len(keys) - len(values))))

    def resolve_row_index_by_id(self, row_id: int | str):
        row_key = str(row_id or "").strip()
        if not row_key:
            return None

        ws = self._get_worksheet()
        ids = ws.col_values(1)
        for row_number, current_id in enumerate(ids[1:], start=2):
            if str(current_id).strip() == row_key:
                return row_number
        return None

    def get_row_by_id(self, row_id: int | str):
        row_number = self.resolve_row_index_by_id(row_id)
        if row_number is None:
            return None
        return self.get_row(row_number)

    def update_cell_by_id(self, row_id: int | str, col: int, value: str) -> bool:
        row_number = self.resolve_row_index_by_id(row_id)
        if row_number is None:
            return False
        self.update_cell(row_number, col, value)
        return True

    def delete_row_by_id(self, row_id: int | str) -> bool:
        row_number = self.resolve_row_index_by_id(row_id)
        if row_number is None:
            return False
        self.delete_row(row_number)
        return True

    def search(self, keyword: str):
        records = self.get_all_records()
        keyword = keyword.lower()
        return [
            r
            for r in records
            if keyword in str(r.get("Tieu de", "")).lower()
            or keyword in str(r.get("Tom tat AI", "")).lower()
            or keyword in str(r.get("Tags", "")).lower()
        ]

    def filter_by(
        self,
        category: str = None,
        priority: str = None,
        status: str = None,
        user: str = None,
    ):
        records = self.get_all_records()
        results = records
        if category:
            results = [
                r for r in results if r.get("Chu de", "").lower() == category.lower()
            ]
        if priority:
            results = [
                r for r in results if r.get("Uu tien", "").lower() == priority.lower()
            ]
        if status:
            results = [
                r for r in results if r.get("Trang thai", "") == status
            ]
        if user:
            results = [r for r in results if user in r.get("Nguoi luu", "")]
        return results
