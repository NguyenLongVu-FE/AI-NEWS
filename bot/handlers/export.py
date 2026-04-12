from datetime import datetime

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.export import ExportService
from bot.services.settings import SettingsService
from bot.services.i18n import t

export_service = ExportService()
settings_service = SettingsService()


async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = settings_service.get_user_settings(str(update.message.from_user.id))["language"]

    processing_msg = await update.message.reply_text(
        f"⏳ {t('export_generating', lang)}", parse_mode="HTML"
    )

    try:
        xlsx_data = export_service.generate_xlsx()
        filename = f"infosaver-export-{datetime.now().strftime('%Y%m%d')}.xlsx"
        await update.message.reply_document(
            document=xlsx_data,
            filename=filename,
            caption=f"📊 {t('export_title', lang)}",
        )
        await processing_msg.delete()
    except Exception as e:
        await processing_msg.edit_text(
            f"❌ {t('error', lang)}\n\n{str(e)}",
            parse_mode="HTML",
        )


export_handler = CommandHandler("export", export_cmd)
