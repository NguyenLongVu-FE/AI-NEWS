import io
from datetime import datetime

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment

from bot.services.sheets import get_sheets_service


class ExportService:
    def __init__(self):
        self._sheets = None

    @property
    def sheets(self):
        if self._sheets is None:
            self._sheets = get_sheets_service()
        return self._sheets

    def generate_xlsx(self) -> bytes:
        records = self.sheets.get_all_records()
        columns = [
            ("ID", "ID"),
            ("Ngay luu", "Ngày lưu"),
            ("Tieu de", "Tiêu đề"),
            ("Link goc", "Link gốc"),
            ("Nguon", "Nguồn"),
            ("Tom tat AI", "Tóm tắt AI"),
            ("Ghi chu tay", "Ghi chú tay"),
            ("Chu de", "Chủ đề"),
            ("Tags", "Từ khóa"),
            ("Nguoi luu", "Người lưu"),
            ("Thumbnail", "Thumbnail"),
        ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "InfoSaver Data"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        for col, (_, display_header) in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col, value=display_header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for row_idx, record in enumerate(records, 2):
            for col_idx, (key, _) in enumerate(columns, 1):
                ws.cell(row=row_idx, column=col_idx, value=record.get(key, ""))

        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 40
        ws.column_dimensions["D"].width = 50
        ws.column_dimensions["E"].width = 12
        ws.column_dimensions["F"].width = 50
        ws.column_dimensions["G"].width = 30
        ws.column_dimensions["H"].width = 15
        ws.column_dimensions["I"].width = 25
        ws.column_dimensions["J"].width = 15
        ws.column_dimensions["K"].width = 30

        ws.freeze_panes = "A2"
        last_column = get_column_letter(len(columns))
        last_row = max(2, len(records) + 1)
        ws.auto_filter.ref = f"A1:{last_column}{last_row}"

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
