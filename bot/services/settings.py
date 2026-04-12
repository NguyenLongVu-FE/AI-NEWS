import gspread

from bot.services.sheets import get_sheets_service

SETTINGS_SHEET_NAME = "Settings"
SETTINGS_HEADERS = ["user_id", "language", "remind_enabled"]


class SettingsService:
    def __init__(self):
        self._sheets = None

    @property
    def sheets(self):
        if self._sheets is None:
            self._sheets = get_sheets_service()
        return self._sheets

    def _get_settings_sheet(self):
        spreadsheet = self.sheets.spreadsheet
        try:
            ws = spreadsheet.worksheet(SETTINGS_SHEET_NAME)
            return ws
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(SETTINGS_SHEET_NAME, rows=100, cols=3)
            ws.update(range_name="A1:C1", values=[SETTINGS_HEADERS])
            return ws

    def get_user_settings(self, user_id: str) -> dict:
        ws = self._get_settings_sheet()
        records = ws.get_all_records()
        for r in records:
            if r.get("user_id", "") == str(user_id):
                return {
                    "language": r.get("language", "vi"),
                    "remind_enabled": r.get("remind_enabled", "true"),
                }
        return {"language": "vi", "remind_enabled": "true"}

    def set_language(self, user_id: str, language: str):
        ws = self._get_settings_sheet()
        records = ws.get_all_records()
        uid = str(user_id)
        for i, r in enumerate(records):
            if r.get("user_id", "") == uid:
                ws.update_cell(i + 2, 2, language)
                return
        ws.append_row([uid, language, "true"])

    def set_remind(self, user_id: str, enabled: bool):
        ws = self._get_settings_sheet()
        records = ws.get_all_records()
        uid = str(user_id)
        val = "true" if enabled else "false"
        for i, r in enumerate(records):
            if r.get("user_id", "") == uid:
                ws.update_cell(i + 2, 3, val)
                return
        ws.append_row([uid, "vi", val])

    def get_all_remind_users(self) -> list:
        ws = self._get_settings_sheet()
        records = ws.get_all_records()
        return [
            r["user_id"]
            for r in records
            if r.get("remind_enabled", "true") == "true"
        ]
