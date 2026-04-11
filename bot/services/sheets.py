from datetime import datetime

import gspread
from gspread.utils import ValueInputOption

from bot.config import GOOGLE_SHEET_ID, SHEET_HEADERS, get_google_credentials


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
        if ws.acell("A1").value != "ID":
            ws.update(range_name="A1:N1", values=[SHEET_HEADERS], value_input_option="RAW")

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
    ):
        ws = self._get_worksheet()
        row_id = self.get_next_id()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            reminder_date,
        ]
        ws.append_row(row, value_input_option=ValueInputOption.raw)
        return row_id

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
