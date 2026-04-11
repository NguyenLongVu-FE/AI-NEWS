import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import MessageHandler, filters, ContextTypes

from bot.services.parser import parse_link_input
from bot.services.scraper import ScraperService
from bot.services.gemini import GeminiService
from bot.services.sheets import get_sheets_service
from bot.services.settings import SettingsService
from bot.services.i18n import t
from bot.utils.formatting import (
    format_save_success,
    format_processing,
    format_error,
)

scraper = ScraperService()
gemini = GeminiService()
settings_service = SettingsService()

URL_REGEX = re.compile(r"https?://\S+")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not URL_REGEX.search(text):
        return

    sheets = get_sheets_service()
    user = update.message.from_user
    user_name = user.first_name or str(user.id)
    lang = settings_service.get_user_settings(str(user.id))["language"]

    parsed = parse_link_input(text)
    url = parsed["url"]

    if not url:
        await update.message.reply_text(
            format_error(
                "Link khong hop le. URL phai bat dau bang http:// hoac https://",
                "Gui lai link dung format",
            ),
            parse_mode="HTML",
        )
        return

    existing_row = sheets.find_by_url(url)
    if existing_row:
        record = sheets.get_row(existing_row)
        if parsed["notes"]:
            sheets.append_note(existing_row, parsed["notes"])
        note_msg = f"📝 <b>{t('notes_merged', lang)}</b>" if parsed["notes"] else ""
        await update.message.reply_text(
            f"🔁 <b>{t('link_exists', lang)}</b>\n\n"
            f"📄 <b>{t('link_title', lang)}</b> {record.get('Tieu de', 'N/A')}\n"
            f"👤 <b>{t('link_saved_by', lang)}</b> {record.get('Nguoi luu', 'N/A')}\n"
            f"{note_msg}",
            parse_mode="HTML",
        )
        return

    processing_msg = await update.message.reply_text(
        format_processing(), parse_mode="HTML"
    )

    metadata = scraper.fetch_metadata(url)
    title = metadata["title"]
    source = metadata["source"]
    thumbnail = metadata["thumbnail"]

    ai_summary = gemini.summarize(title, metadata["description"], url)

    if not ai_summary and metadata["success"]:
        ai_summary = metadata.get("description", "")[:300]
    elif not ai_summary:
        ai_summary = "Chua co tom tat"

    row_id = sheets.append_link(
        url=url,
        title=title,
        source=source,
        ai_summary=ai_summary,
        notes=parsed["notes"],
        category=parsed["category"],
        tags=", ".join(parsed["tags"]),
        priority=parsed["priority"],
        status="chua_doc",
        user_name=user_name,
        thumbnail=thumbnail,
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👁 View Details", callback_data=f"v:{row_id}"
                ),
                InlineKeyboardButton(
                    "✏️ Edit", callback_data=f"a:edit:{row_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🗑️ Delete", callback_data=f"a:del:{row_id}"
                )
            ],
        ]
    )

    success_text = format_save_success(
        title, source, parsed["category"], parsed["priority"], ai_summary, row_id
    )

    try:
        await processing_msg.edit_text(
            success_text, parse_mode="HTML", reply_markup=keyboard
        )
    except Exception:
        await update.message.reply_text(
            success_text, parse_mode="HTML", reply_markup=keyboard
        )

    if not metadata["success"]:
        try:
            await update.message.reply_text(
                f"⚠️ <b>{t('save_warning', lang)}</b>\n\n"
                f"❌ {t('save_warning_desc', lang)} {metadata['error']}\n\n"
                f"{t('save_warning_hint', lang, id=row_id)}",
                parse_mode="HTML",
            )
        except Exception:
            pass


link_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)
