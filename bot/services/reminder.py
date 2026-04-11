from datetime import datetime, timedelta

from bot.services.sheets import get_sheets_service
from bot.services.settings import SettingsService
from bot.services.i18n import t


class ReminderService:
    def __init__(self):
        self.sheets = get_sheets_service()
        self.settings = SettingsService()

    def get_digest(self, user_id: str) -> str:
        lang = self.settings.get_user_settings(user_id)["language"]

        high_unread = self.sheets.filter_by(priority="high", status="chua_doc")
        stale_reading = self.sheets.filter_by(status="dang_doc")

        three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        urgent = [
            r for r in high_unread
            if str(r.get("Ngay luu", ""))[:10] <= three_days_ago
        ]
        stale = [
            r for r in stale_reading
            if str(r.get("Ngay luu", ""))[:10] <= seven_days_ago
        ]

        if not urgent and not stale:
            return None

        text = f"🌅 <b>{t('digest_title', lang)}</b>\n\n"
        if urgent:
            text += f"🔴 {len(urgent)} {t('digest_high_unread', lang)}\n"
        if stale:
            text += f"📖 {len(stale)} {t('digest_stale_reading', lang)}\n"
        text += f"\n💡 {t('digest_hint', lang)}"
        return text

    def get_all_digests(self) -> list:
        user_ids = self.settings.get_all_remind_users()
        digests = []
        for uid in user_ids:
            digest = self.get_digest(uid)
            if digest:
                digests.append({"user_id": uid, "message": digest})
        return digests
