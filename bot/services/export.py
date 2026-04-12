import io
from datetime import datetime

import openpyxl
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
        headers = [
            "ID", "Ngay luu", "Tieu de", "Link goc", "Nguon",
            "Tom tat AI", "Ghi chu tay", "Chu de", "Tags",
            "Uu tien", "Trang thai", "Nguoi luu", "Thumbnail", "Nhac nho",
        ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "InfoSaver Data"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for row_idx, record in enumerate(records, 2):
            for col_idx, key in enumerate(headers, 1):
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
        ws.column_dimensions["J"].width = 10
        ws.column_dimensions["K"].width = 15
        ws.column_dimensions["L"].width = 15
        ws.column_dimensions["M"].width = 30
        ws.column_dimensions["N"].width = 15

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
