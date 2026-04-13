from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.i18n import t
from bot.services.settings import SettingsService

settings_service = SettingsService()


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


async def lib_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    await update.message.reply_text(
        f"ℹ️ {t('lib_deprecated_use_topics', lang)}",
        parse_mode="HTML",
    )


lib_handler = CommandHandler("lib", lib_cmd)
