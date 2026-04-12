import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import MessageHandler, filters, ContextTypes

from bot.services.parser import parse_link_input
from bot.services.library_groups import detect_library_group, normalize_library_group
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
from bot.utils.validation import validate_url, sanitize_html, validate_tags

scraper = ScraperService()
gemini = GeminiService()
settings_service = SettingsService()

URL_REGEX = re.compile(r"https?://\S+")


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


def _get_row_by_logical_id(sheets, row_id: int):
    if hasattr(sheets, "get_row_by_id"):
        return sheets.get_row_by_id(row_id)
    return sheets.get_row(row_id)


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not URL_REGEX.search(text):
        return

    sheets = get_sheets_service()
    user = update.message.from_user
    user_name = user.first_name or str(user.id)
    lang = _get_lang(update)

    parsed = parse_link_input(text)
    url = parsed["url"]

    if not url:
        await update.message.reply_text(
            format_error(
                t("invalid_url", lang),
                t("retry_with_valid_link", lang),
                lang=lang,
            ),
            parse_mode="HTML",
        )
        return

    valid, msg = validate_url(url)
    if not valid:
        await update.message.reply_text(
            format_error(msg, lang=lang), parse_mode="HTML"
        )
        return

    tags_valid, tags_msg = validate_tags(parsed["tags"])
    if not tags_valid:
        parsed["tags"] = parsed["tags"][:10]

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
        format_processing(lang), parse_mode="HTML"
    )

    metadata = scraper.fetch_metadata(url)
    title = sanitize_html(metadata["title"])
    source = metadata["source"]
    thumbnail = metadata["thumbnail"]

    ai_summary = gemini.summarize(title, metadata["description"], url)

    if not ai_summary and metadata["success"]:
        ai_summary = metadata.get("description", "")[:300]
    elif not ai_summary:
        ai_summary = t("no_summary", lang)

    library_group = normalize_library_group(parsed.get("library_group_override"))
    if not library_group:
        library_group = detect_library_group(url, title, ai_summary)

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
        library_group=library_group,
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("view_details_button", lang), callback_data=f"v:{row_id}"
                ),
                InlineKeyboardButton(
                    t("edit_button", lang), callback_data=f"a:edit:{row_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    t("delete_button", lang), callback_data=f"a:del:{row_id}"
                )
            ],
        ]
    )

    success_text = format_save_success(
        title, source, parsed["category"], parsed["priority"], ai_summary, row_id, lang=lang
    )

    try:
        await processing_msg.edit_text(
            success_text, parse_mode="HTML", reply_markup=keyboard
        )
    except Exception:
        await update.message.reply_text(
            success_text, parse_mode="HTML", reply_markup=keyboard
        )

    try:
        saved_record = _get_row_by_logical_id(sheets, row_id)
        if saved_record:
            sheets.upsert_library_row(saved_record)
    except Exception:
        pass

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
