from collections import Counter
from datetime import datetime, timedelta

from bot.services.sheets import get_sheets_service


class StatsService:
    def __init__(self):
        self._sheets = None

    @property
    def sheets(self):
        if self._sheets is None:
            self._sheets = get_sheets_service()
        return self._sheets

    def get_stats(self, period: str = "month") -> dict:
        records = self.sheets.get_all_records()

        if period == "week":
            cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            cutoff = datetime.now().replace(day=1).strftime("%Y-%m-%d")

        filtered = [
            r for r in records
            if str(r.get("Ngay luu", ""))[:10] >= cutoff
        ]

        total = len(filtered)
        read_count = sum(
            1 for r in filtered
            if r.get("Trang thai", "") in ("da_nghien_cuu", "da_ap_dung")
        )
        unread_count = sum(
            1 for r in filtered if r.get("Trang thai", "") == "chua_doc"
        )

        contributors = Counter(str(r.get("Nguoi luu", "")) for r in filtered)
        categories = Counter(str(r.get("Chu de", "")) for r in filtered)
        sources = Counter(str(r.get("Nguon", "")) for r in filtered)

        all_tags = []
        for r in filtered:
            tag_str = r.get("Tags", "")
            if tag_str:
                for tag in tag_str.split(","):
                    tag = tag.strip()
                    if tag:
                        all_tags.append(tag)
        tags = Counter(all_tags)

        return {
            "total": total,
            "read": read_count,
            "unread": unread_count,
            "contributors": contributors.most_common(5),
            "categories": categories.most_common(5),
            "sources": sources.most_common(),
            "tags": tags.most_common(5),
        }


def emoji_bar(value: int, total: int, length: int = 10) -> str:
    if total == 0:
        return "⬜" * length
    filled = round((value / total) * length)
    return "🟩" * filled + "⬜" * (length - filled)
