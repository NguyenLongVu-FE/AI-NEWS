from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.i18n import t
from bot.services.settings import SettingsService
from bot.services.sheets import get_sheets_service
from bot.utils.formatting import format_empty_state

settings_service = SettingsService()


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


async def topics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    sheets = get_sheets_service()
    counts = sheets.list_topic_counts()
    total = sum(counts.values())

    if not counts:
        await update.message.reply_text(
            format_empty_state(t("topics_empty", lang), lang=lang),
            parse_mode="HTML",
        )
        return

    rows = "\n".join(
        f"• <b>{topic}</b>: {count}"
        for topic, count in counts.items()
    )
    text = (
        f"🗂️ <b>{t('topics_title', lang)}</b>\n"
        f"{t('stats_total', lang)}: <b>{total}</b>\n\n"
        f"{rows}"
    )
    await update.message.reply_text(text[:4096], parse_mode="HTML")


topics_handler = CommandHandler("topics", topics_cmd)
