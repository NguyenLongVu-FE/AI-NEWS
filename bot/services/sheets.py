from collections import Counter
from datetime import datetime, timedelta
import logging
import re
import textwrap
from typing import Optional, Union

import gspread
from gspread.utils import ValueInputOption, rowcol_to_a1

from bot.config import (
    GOOGLE_SHEET_ID,
    SHEET_HEADERS,
    SHEET_DISPLAY_HEADERS,
    TOPIC_SHEET_PREFIX,
    get_google_credentials,
)
from bot.services.category import normalize_category_name


_instance = None
logger = logging.getLogger(__name__)
_HEADER_TO_DISPLAY = dict(zip(SHEET_HEADERS, SHEET_DISPLAY_HEADERS))
_DISPLAY_TO_HEADER = {display: header for header, display in _HEADER_TO_DISPLAY.items()}
_DISPLAY_TO_HEADER.update({header: header for header in SHEET_HEADERS})
_TOPIC_SLUG_RE = re.compile(r"[^a-z0-9]+")
_DEFAULT_TOPIC = "Tech"
_DASHBOARD_SHEET_NAME = "DASHBOARD"
_DASHBOARD_TABLE_HEADERS = [
    "Chủ đề",
    "Sheet",
    "Tổng links",
    "Mới hôm nay",
    "Mới 7 ngày",
    "Top 5 từ khóa",
    "URL",
]


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
        self._bootstrap_topic_workspace()

    @staticmethod
    def _sheet_id(ws):
        return (getattr(ws, "_properties", {}) or {}).get("sheetId")

    @staticmethod
    def _sheet_header_range() -> str:
        return f"A1:{rowcol_to_a1(1, len(SHEET_HEADERS))}"

    @staticmethod
    def _normalize_record_keys(record: dict) -> dict:
        normalized = {}
        for key, value in (record or {}).items():
            canonical_key = _DISPLAY_TO_HEADER.get(str(key).strip(), "")
            if canonical_key in SHEET_HEADERS:
                normalized[canonical_key] = value
        for header in SHEET_HEADERS:
            normalized.setdefault(header, "")
        return normalized

    @staticmethod
    def _topic_slug(topic: str) -> str:
        cleaned = _TOPIC_SLUG_RE.sub("-", str(topic or "").strip().lower()).strip("-")
        return cleaned or "tech"

    @classmethod
    def _topic_sheet_name(cls, topic: str) -> str:
        return f"{TOPIC_SHEET_PREFIX}{cls._topic_slug(topic)}"

    @classmethod
    def _is_topic_sheet(cls, title: str) -> bool:
        return str(title or "").startswith(TOPIC_SHEET_PREFIX)

    @classmethod
    def _topic_from_sheet_title(cls, title: str) -> str:
        slug = str(title or "").removeprefix(TOPIC_SHEET_PREFIX)
        value = slug.replace("-", " ").strip().title()
        return value or _DEFAULT_TOPIC

    @staticmethod
    def _normalize_topic_value(topic: Optional[str]) -> str:
        normalized = normalize_category_name(topic)
        if normalized:
            return normalized
        raw = str(topic or "").strip()
        return raw or _DEFAULT_TOPIC

    @staticmethod
    def _normalize_keyword_token(value: str) -> str:
        token = _TOPIC_SLUG_RE.sub("-", str(value or "").strip().lower()).strip("-")
        return token

    @classmethod
    def _normalize_keyword_value(cls, raw_keywords: Union[str, list[str], tuple[str, ...]]) -> str:
        if isinstance(raw_keywords, (list, tuple)):
            parts = []
            for item in raw_keywords:
                parts.extend(re.split(r"[,\n]", str(item)))
        else:
            parts = re.split(r"[,\n]", str(raw_keywords or ""))

        ordered: list[str] = []
        seen = set()
        for part in parts:
            token = cls._normalize_keyword_token(part)
            if not token or token in seen:
                continue
            seen.add(token)
            ordered.append(token)
        return ", ".join(ordered)

    @staticmethod
    def _format_ai_summary_value(ai_summary: str) -> str:
        raw = str(ai_summary or "").strip()
        if not raw:
            return ""

        if "\n" in raw:
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            return "\n".join(lines)

        normalized = re.sub(r"\s+", " ", raw).strip()
        sentences = [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+", normalized)
            if part.strip()
        ]
        if len(sentences) > 1:
            return "\n".join(sentences)

        chunks = textwrap.wrap(
            normalized,
            width=110,
            break_long_words=False,
            break_on_hyphens=False,
        )
        return "\n".join(chunks) if chunks else normalized

    def _topic_worksheets(self):
        worksheets = self.spreadsheet.worksheets()
        topics = [ws for ws in worksheets if self._is_topic_sheet(ws.title)]
        return sorted(topics, key=lambda ws: ws.title.lower())

    def _topic_worksheet_by_name(self, name: str):
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            return None

    def _dashboard_worksheet(self):
        try:
            return self.spreadsheet.worksheet(_DASHBOARD_SHEET_NAME)
        except gspread.WorksheetNotFound:
            return None

    def _ensure_dashboard_worksheet(self):
        ws = self._dashboard_worksheet()
        if ws is not None:
            return ws
        return self.spreadsheet.add_worksheet(
            title=_DASHBOARD_SHEET_NAME,
            rows=1000,
            cols=len(_DASHBOARD_TABLE_HEADERS),
        )

    def _ensure_topic_headers(self, ws):
        current_headers = ws.row_values(1)
        if current_headers != SHEET_DISPLAY_HEADERS:
            ws.update(
                range_name=self._sheet_header_range(),
                values=[SHEET_DISPLAY_HEADERS],
                value_input_option="RAW",
            )
        self._apply_sheet_visuals(ws)

    def _create_topic_worksheet(self, topic: str):
        ws = self.spreadsheet.add_worksheet(
            title=self._topic_sheet_name(topic),
            rows=1000,
            cols=len(SHEET_HEADERS),
        )
        ws.update(
            range_name=self._sheet_header_range(),
            values=[SHEET_DISPLAY_HEADERS],
            value_input_option="RAW",
        )
        self._apply_sheet_visuals(ws)
        return ws

    def _ensure_topic_worksheet(self, topic: str):
        topic_value = self._normalize_topic_value(topic)
        name = self._topic_sheet_name(topic_value)
        ws = self._topic_worksheet_by_name(name)
        if ws is not None:
            self._ensure_topic_headers(ws)
            return ws
        return self._create_topic_worksheet(topic_value)

    def _bootstrap_topic_workspace(self):
        topic_sheets = self._topic_worksheets()
        if topic_sheets:
            for ws in topic_sheets:
                self._ensure_topic_headers(ws)
            self._safe_rebuild_dashboard()
            return

        for ws in self.spreadsheet.worksheets():
            if ws.title in ("Settings", _DASHBOARD_SHEET_NAME):
                continue
            try:
                self.spreadsheet.del_worksheet(ws)
            except Exception:
                logger.warning(
                    "Unable to delete worksheet=%s during bootstrap; resetting it as empty topic sheet",
                    ws.title,
                    exc_info=True,
                )
                try:
                    ws.clear()
                    ws.update_title(self._topic_sheet_name(_DEFAULT_TOPIC))
                    self._ensure_topic_headers(ws)
                except Exception:
                    logger.warning("Unable to reset worksheet=%s during bootstrap", ws.title, exc_info=True)
        self._safe_rebuild_dashboard()

    def _apply_sheet_visuals(self, ws):
        sheet_id = self._sheet_id(ws)
        if sheet_id is None:
            return
        summary_col = SHEET_HEADERS.index("Tom tat AI")

        requests = [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(SHEET_HEADERS),
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.2627,
                                "green": 0.4470,
                                "blue": 0.7686,
                            },
                            "horizontalAlignment": "CENTER",
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0,
                                },
                                "bold": True,
                            },
                        }
                    },
                    "fields": (
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    ),
                }
            },
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "startColumnIndex": 0,
                            "endColumnIndex": len(SHEET_HEADERS),
                        }
                    }
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": summary_col,
                        "endIndex": summary_col + 1,
                    },
                    "properties": {"pixelSize": 380},
                    "fields": "pixelSize",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": summary_col,
                        "endColumnIndex": summary_col + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "WRAP",
                            "verticalAlignment": "TOP",
                        }
                    },
                    "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)",
                }
            },
        ]

        try:
            self.spreadsheet.batch_update({"requests": requests})
        except Exception:
            logger.warning(
                "Unable to apply sheet visuals for worksheet=%s",
                getattr(ws, "title", "?"),
                exc_info=True,
            )

    def _apply_dashboard_visuals(self, ws, table_header_row: int, total_rows: int):
        sheet_id = self._sheet_id(ws)
        if sheet_id is None:
            return

        header_row_start = max(table_header_row - 1, 0)
        requests = [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": table_header_row},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": header_row_start,
                        "endRowIndex": header_row_start + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": len(_DASHBOARD_TABLE_HEADERS),
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.2627,
                                "green": 0.4470,
                                "blue": 0.7686,
                            },
                            "horizontalAlignment": "CENTER",
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0,
                                },
                                "bold": True,
                            },
                        }
                    },
                    "fields": (
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    ),
                }
            },
            {
                "setBasicFilter": {
                    "filter": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": header_row_start,
                            "endRowIndex": max(total_rows, table_header_row),
                            "startColumnIndex": 0,
                            "endColumnIndex": len(_DASHBOARD_TABLE_HEADERS),
                        }
                    }
                }
            },
        ]

        try:
            self.spreadsheet.batch_update({"requests": requests})
        except Exception:
            logger.warning(
                "Unable to apply dashboard visuals for worksheet=%s",
                getattr(ws, "title", "?"),
                exc_info=True,
            )

    def rebuild_dashboard_sheet(self):
        ws = self._ensure_dashboard_worksheet()
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        topic_rows = []
        total_links = 0
        for topic_ws in self._topic_worksheets():
            records = [
                self._normalize_record_keys(record)
                for record in topic_ws.get_all_records()
            ]
            topic_name = (
                str(records[0].get("Chu de", "")).strip()
                if records and str(records[0].get("Chu de", "")).strip()
                else self._topic_from_sheet_title(topic_ws.title)
            )
            total_count = len(records)
            total_links += total_count
            today_count = sum(
                1
                for record in records
                if str(record.get("Ngay luu", "")).startswith(today)
            )
            week_count = sum(
                1
                for record in records
                if str(record.get("Ngay luu", ""))[:10] >= week_ago
            )
            keyword_counts = Counter()
            for record in records:
                for keyword in str(record.get("Tags", "")).split(","):
                    token = self._normalize_keyword_token(keyword)
                    if token:
                        keyword_counts[token] += 1
            top_keywords = ", ".join(
                f"{keyword}({count})"
                for keyword, count in keyword_counts.most_common(5)
            )
            sheet_id = self._sheet_id(topic_ws)
            sheet_url = (
                f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit#gid={sheet_id}"
                if sheet_id is not None
                else ""
            )
            topic_rows.append(
                [
                    topic_name,
                    topic_ws.title,
                    total_count,
                    today_count,
                    week_count,
                    top_keywords,
                    sheet_url,
                ]
            )

        topic_rows.sort(key=lambda row: (-int(row[2]), str(row[0]).lower()))

        values = [
            ["DASHBOARD"],
            ["Tổng links", total_links],
            ["Tổng chủ đề", len(topic_rows)],
            ["Cập nhật lần cuối", updated_at],
            [],
            _DASHBOARD_TABLE_HEADERS,
            *topic_rows,
        ]
        ws.clear()
        ws.update(
            range_name="A1",
            values=values,
            value_input_option="RAW",
        )
        self._apply_dashboard_visuals(
            ws,
            table_header_row=6,
            total_rows=len(values),
        )

    def _safe_rebuild_dashboard(self):
        try:
            self.rebuild_dashboard_sheet()
        except Exception:
            logger.warning("Unable to rebuild dashboard sheet", exc_info=True)

    def _all_records_with_location(self):
        located = []
        for ws in self._topic_worksheets():
            for row_number, record in enumerate(ws.get_all_records(), start=2):
                normalized = self._normalize_record_keys(record)
                if not normalized.get("Chu de"):
                    normalized["Chu de"] = self._topic_from_sheet_title(ws.title)
                located.append((ws, row_number, normalized))
        return located

    def _locate_row_by_id(self, row_id: Union[int, str]):
        row_key = str(row_id or "").strip()
        if not row_key:
            return None
        for ws, row_number, record in self._all_records_with_location():
            if str(record.get("ID", "")).strip() == row_key:
                return ws, row_number, record
        return None

    def list_topic_counts(self) -> dict[str, int]:
        counts = {}
        for ws in self._topic_worksheets():
            records = [self._normalize_record_keys(record) for record in ws.get_all_records()]
            if records and records[0].get("Chu de"):
                topic_name = str(records[0]["Chu de"]).strip()
            else:
                topic_name = self._topic_from_sheet_title(ws.title)
            counts[topic_name] = len(records)
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0].lower())))

    def get_next_id(self):
        max_id = 0
        for record in self.get_all_records():
            try:
                max_id = max(max_id, int(str(record.get("ID", "")).strip()))
            except (TypeError, ValueError):
                continue
        return max_id + 1

    def find_by_url(self, url: str):
        target = str(url or "").strip()
        if not target:
            return None
        for _, _, record in self._all_records_with_location():
            if str(record.get("Link goc", "")).strip() == target:
                return str(record.get("ID", "")).strip() or None
        return None

    def append_link(
        self,
        url: str,
        title: str,
        source: str,
        ai_summary: str,
        notes: str,
        category: str,
        tags: Union[str, list[str], tuple[str, ...]],
        user_name: str,
        thumbnail: str,
    ):
        topic = self._normalize_topic_value(category)
        ws = self._ensure_topic_worksheet(topic)
        row_id = self.get_next_id()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            row_id,
            now,
            title,
            url,
            source,
            self._format_ai_summary_value(ai_summary),
            notes,
            topic,
            self._normalize_keyword_value(tags),
            user_name,
            thumbnail,
        ]
        ws.append_row(row, value_input_option=ValueInputOption.raw)
        self._safe_rebuild_dashboard()
        return row_id

    def update_cell(self, row: int, col: int, value: str):
        topic_sheets = self._topic_worksheets()
        if not topic_sheets:
            return
        topic_sheets[0].update_cell(row, col, value)

    def append_note(self, row: int, note: str):
        topic_sheets = self._topic_worksheets()
        if not topic_sheets:
            return
        ws = topic_sheets[0]
        current = ws.cell(row, 7).value or ""
        separator = " | " if current else ""
        ws.update_cell(row, 7, f"{current}{separator}{note}")

    def append_note_by_id(self, row_id: Union[int, str], note: str) -> bool:
        located = self._locate_row_by_id(row_id)
        if located is None:
            return False
        ws, row_number, _ = located
        current = ws.cell(row_number, 7).value or ""
        separator = " | " if current else ""
        ws.update_cell(row_number, 7, f"{current}{separator}{note}")
        self._safe_rebuild_dashboard()
        return True

    def merge_keywords_by_id(
        self, row_id: Union[int, str], keywords: Union[str, list[str], tuple[str, ...]]
    ) -> bool:
        located = self._locate_row_by_id(row_id)
        if located is None:
            return False
        ws, row_number, record = located
        existing = str(record.get("Tags", "")).strip()
        merged = self._normalize_keyword_value([existing, keywords])
        ws.update_cell(row_number, SHEET_HEADERS.index("Tags") + 1, merged)
        self._safe_rebuild_dashboard()
        return True

    def get_all_records(self):
        records = [record for _, _, record in self._all_records_with_location()]

        def _sort_key(record: dict) -> int:
            try:
                return int(str(record.get("ID", "")).strip() or "0")
            except ValueError:
                return 0

        return sorted(
            records,
            key=_sort_key,
        )

    def delete_row(self, row: int):
        topic_sheets = self._topic_worksheets()
        if not topic_sheets:
            return
        topic_sheets[0].delete_rows(row)

    def get_row(self, row: int):
        topic_sheets = self._topic_worksheets()
        if not topic_sheets:
            return None
        values = topic_sheets[0].row_values(row)
        if not values:
            return None
        keys = SHEET_HEADERS
        return dict(zip(keys, values + [""] * (len(keys) - len(values))))

    def resolve_row_index_by_id(self, row_id: Union[int, str]):
        located = self._locate_row_by_id(row_id)
        if located is None:
            return None
        _, row_number, _ = located
        return row_number

    def get_row_by_id(self, row_id: Union[int, str]):
        located = self._locate_row_by_id(row_id)
        if located is None:
            return None
        _, _, record = located
        return record

    def update_cell_by_id(self, row_id: Union[int, str], col: int, value: str) -> bool:
        located = self._locate_row_by_id(row_id)
        if located is None:
            return False
        ws, row_number, _ = located
        ws.update_cell(row_number, col, value)
        self._safe_rebuild_dashboard()
        return True

    def delete_row_by_id(self, row_id: Union[int, str]) -> bool:
        located = self._locate_row_by_id(row_id)
        if located is None:
            return False
        ws, row_number, _ = located
        ws.delete_rows(row_number)
        self._safe_rebuild_dashboard()
        return True

    def move_row_to_topic_by_id(self, row_id: Union[int, str], topic: str) -> bool:
        located = self._locate_row_by_id(row_id)
        if located is None:
            return False

        current_ws, row_number, record = located
        topic_value = self._normalize_topic_value(topic)
        target_ws = self._ensure_topic_worksheet(topic_value)
        target_sheet_name = self._topic_sheet_name(topic_value)
        record["Chu de"] = topic_value
        row = [record.get(header, "") for header in SHEET_HEADERS]

        if current_ws.title == target_sheet_name:
            current_ws.update(
                range_name=f"A{row_number}:{rowcol_to_a1(row_number, len(SHEET_HEADERS))}",
                values=[row],
                value_input_option="RAW",
            )
            self._safe_rebuild_dashboard()
            return True

        target_ws.append_row(row, value_input_option=ValueInputOption.raw)
        current_ws.delete_rows(row_number)
        self._safe_rebuild_dashboard()
        return True

    def search(self, keyword: str):
        records = self.get_all_records()
        needle = str(keyword or "").strip().lower()
        if not needle:
            return []
        return [
            r
            for r in records
            if needle in str(r.get("Tieu de", "")).lower()
            or needle in str(r.get("Tom tat AI", "")).lower()
            or needle in str(r.get("Tags", "")).lower()
            or needle in str(r.get("Chu de", "")).lower()
        ]

    def filter_by(
        self,
        category: str = None,
        keyword: str = None,
        user: str = None,
    ):
        records = self.get_all_records()
        results = records
        if category:
            category_value = self._normalize_topic_value(category)
            results = [
                r
                for r in results
                if self._normalize_topic_value(r.get("Chu de", "")) == category_value
            ]
        if keyword:
            token = self._normalize_keyword_token(keyword)
            results = [
                r
                for r in results
                if token in [self._normalize_keyword_token(k) for k in str(r.get("Tags", "")).split(",")]
            ]
        if user:
            user_key = str(user).strip().lower()
            results = [
                r for r in results if user_key in str(r.get("Nguoi luu", "")).lower()
            ]
        return results
