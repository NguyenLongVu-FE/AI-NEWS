from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.settings import SettingsService
from bot.services.i18n import t

settings_service = SettingsService()


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ("vi", "en"):
        user_id = str(update.message.from_user.id)
        current = settings_service.get_user_settings(user_id)["language"]
        await update.message.reply_text(
            f"🌐 <b>Language / Ngôn ngữ</b>\n\n"
            f"Current: {'🇻🇳 Tiếng Việt' if current == 'vi' else '🇬🇧 English'}\n\n"
            f"/lang vi — Tiếng Việt\n"
            f"/lang en — English",
            parse_mode="HTML",
        )
        return

    lang = context.args[0].lower()
    user_id = str(update.message.from_user.id)
    settings_service.set_language(user_id, lang)

    label = "🇻🇳 Tiếng Việt" if lang == "vi" else "🇬🇧 English"
    await update.message.reply_text(
        f"✅ {t('lang_changed', lang)} {label}",
        parse_mode="HTML",
    )


lang_handler = CommandHandler("lang", lang_cmd)
