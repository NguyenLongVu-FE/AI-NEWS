from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.settings import SettingsService
from bot.services.i18n import t

settings_service = SettingsService()


async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    lang = settings_service.get_user_settings(user_id)["language"]

    if not context.args or context.args[0].lower() not in ("on", "off"):
        current = settings_service.get_user_settings(user_id)["remind_enabled"]
        status = "ON ✅" if current == "true" else "OFF ❌"
        await update.message.reply_text(
            f"⏰ <b>Reminder / Nhắc nhở</b>\n\n"
            f"Status: {status}\n\n"
            f"/remind on — Bật daily digest\n"
            f"/remind off — Tắt daily digest",
            parse_mode="HTML",
        )
        return

    action = context.args[0].lower()
    enabled = action == "on"
    settings_service.set_remind(user_id, enabled)

    msg = t("remind_on" if enabled else "remind_off", lang)
    await update.message.reply_text(f"✅ {msg}", parse_mode="HTML")


remind_handler = CommandHandler("remind", remind_cmd)
