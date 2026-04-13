from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.settings import SettingsService
from bot.services.i18n import t

settings_service = SettingsService()


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    first_name = user.first_name or "ban"
    lang = _get_lang(update)
    text = (
        f"👋 {t('start_greeting', lang, name=first_name)}\n\n"
        f"{t('start_bot_name', lang)} — {t('start_description', lang)}\n\n"
        f"<b>{t('start_howto', lang)}</b>\n"
        f"▸ {t('start_send_link', lang)}\n"
        f"▸ {t('start_with_tags', lang)}\n"
        f"▸ {t('start_commands', lang)}\n\n"
        f"<b>{t('start_main_commands', lang)}</b>\n"
        f"{t('start_search', lang)}\n"
        f"{t('start_filter', lang)}\n"
        f"{t('start_topics', lang)}\n"
        f"{t('start_help', lang)}\n\n"
        f"{t('start_cta', lang)}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    text = (
        f"📖 <b>{t('help_title', lang)}</b>\n\n"
        f"<b>📝 {t('help_save_link', lang)}</b>\n"
        f"▸ {t('help_send_link', lang)}\n"
        f"▸ {t('help_with_tags', lang)}\n\n"
        f"<b>🔍 {t('help_search', lang)}</b>\n"
        f"/search <i>{t('search_keyword_placeholder', lang)}</i>\n"
        f"/filter <i>@topic #keyword</i>\n"
        f"/tags — {t('tags_title', lang)}\n"
        f"/topics — {t('topics_title', lang)}\n"
        f"/today — {t('today_short', lang)}\n"
        f"/week — {t('week_short', lang)}\n"
        f"<b>⚙️ {t('help_manage', lang)}</b>\n"
        f"/view <i>ID</i>\n"
        f"/note <i>ID</i> <i>content</i>\n"
        f"/edit <i>ID</i> <i>field</i> <i>value</i>\n"
        f"/delete <i>ID</i>\n\n"
        f"<b>📤 {t('help_export', lang)}</b>\n"
        f"{t('help_export_desc', lang)}\n\n"
        f"<b>🌐 {t('help_lang', lang)}</b>\n"
        f"{t('help_lang_desc', lang)}\n\n"
        f"<b>📊 {t('help_stats', lang)}</b>\n"
        f"{t('help_stats_desc', lang)}\n"
        f"/stats week — {t('stats_week', lang)}\n\n"
        f"<b>📊 {t('other_section', lang)}:</b>\n"
        f"/sheet — {t('sheet_title', lang)}\n"
        f"/addcategory <i>name</i> — (admin)"
    )
    await update.message.reply_text(text, parse_mode="HTML")


start_handler = CommandHandler("start", start)
help_handler = CommandHandler("help", help_command)
