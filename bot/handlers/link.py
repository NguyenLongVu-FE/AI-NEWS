import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, filters

from bot.services.category import detect_category
from bot.services.editing import apply_record_edit
from bot.services.gemini import GeminiService
from bot.services.i18n import t
from bot.services.keywords import detect_keywords
from bot.services.parser import parse_link_input
from bot.services.scraper import ScraperService
from bot.services.settings import SettingsService
from bot.services.sheets import get_sheets_service
from bot.utils.formatting import (
    format_error,
    format_processing,
    format_save_success,
    format_view_detail,
)
from bot.utils.validation import sanitize_html, validate_tags, validate_url

scraper = ScraperService()
gemini = GeminiService()
settings_service = SettingsService()

URL_REGEX = re.compile(r"https?://\S+")


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


async def _handle_existing_link(update: Update, sheets, parsed: dict, existing_id: str, lang: str):
    record = sheets.get_row_by_id(existing_id) or {}
    merged_notes = False
    merged_keywords = False

    if parsed["notes"]:
        merged_notes = sheets.append_note_by_id(existing_id, parsed["notes"])
    if parsed["tags"]:
        merged_keywords = sheets.merge_keywords_by_id(existing_id, parsed["tags"])

    updated_record = sheets.get_row_by_id(existing_id) or record
    notices = []
    if merged_notes:
        notices.append(f"📝 <b>{t('notes_merged', lang)}</b>")
    if merged_keywords:
        notices.append(f"🏷 <b>{t('keywords_merged', lang)}</b>")

    notice_text = f"\n{'\n'.join(notices)}" if notices else ""
    await update.message.reply_text(
        f"🔁 <b>{t('link_exists', lang)}</b>\n\n"
        f"📄 <b>{t('link_title', lang)}</b> {updated_record.get('Tieu de', 'N/A')}\n"
        f"👤 <b>{t('link_saved_by', lang)}</b> {updated_record.get('Nguoi luu', 'N/A')}"
        f"{notice_text}",
        parse_mode="HTML",
    )


def _detail_keyboard(row_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("edit_button", lang), callback_data=f"a:edit:{row_id}"
                ),
                InlineKeyboardButton(
                    t("delete_button", lang), callback_data=f"a:del:{row_id}"
                ),
            ],
        ]
    )


async def _consume_pending_edit_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, sheets, lang: str
) -> bool:
    pending_edit = context.user_data.get("pending_edit")
    if not isinstance(pending_edit, dict):
        return False

    row_id = pending_edit.get("row_id")
    field = pending_edit.get("field", "")
    try:
        logical_id = int(row_id)
    except (TypeError, ValueError):
        context.user_data.pop("pending_edit", None)
        return False

    value = (update.message.text or "").strip()
    result = apply_record_edit(
        sheets,
        row_id=logical_id,
        field=field,
        value=value,
        lang=lang,
    )
    if not result["ok"]:
        if result.get("clear_pending"):
            context.user_data.pop("pending_edit", None)
        await update.message.reply_text(
            format_error(result["error"], lang=lang),
            parse_mode="HTML",
        )
        return True

    context.user_data.pop("pending_edit", None)
    updated_record = result.get("record") or sheets.get_row_by_id(logical_id)
    await update.message.reply_text(
        f"✅ <b>{t('edit_updated', lang)}</b>\n\n"
        f"✏️ {result['field']}: → {result['value']}",
        parse_mode="HTML",
    )
    if updated_record:
        await update.message.reply_text(
            format_view_detail(updated_record, lang=lang),
            parse_mode="HTML",
            reply_markup=_detail_keyboard(logical_id, lang),
        )
    return True


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    sheets = get_sheets_service()
    lang = _get_lang(update)
    if await _consume_pending_edit_input(update, context, sheets, lang):
        return
    if not URL_REGEX.search(text):
        return

    user = update.message.from_user
    user_name = user.first_name or str(user.id)

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

    tags_valid, _ = validate_tags(parsed["tags"])
    if not tags_valid:
        parsed["tags"] = parsed["tags"][:10]

    existing_id = sheets.find_by_url(url)
    if existing_id:
        await _handle_existing_link(update, sheets, parsed, existing_id, lang)
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

    detected_category = detect_category(
        url=url,
        title=title,
        description=metadata.get("description", ""),
        summary=ai_summary,
        tags=parsed.get("tags", []),
    )
    final_category = parsed.get("category") or detected_category
    final_keywords = detect_keywords(
        url=url,
        title=title,
        summary=ai_summary,
        topic=final_category,
        manual_keywords=parsed.get("tags", []),
    )

    row_id = sheets.append_link(
        url=url,
        title=title,
        source=source,
        ai_summary=ai_summary,
        notes=parsed["notes"],
        category=final_category,
        tags=final_keywords,
        user_name=user_name,
        thumbnail=thumbnail,
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
        title, source, final_category, ai_summary, row_id, lang=lang
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
        await update.message.reply_text(
            f"⚠️ <b>{t('save_warning', lang)}</b>\n\n"
            f"❌ {t('save_warning_desc', lang)} {metadata['error']}\n\n"
            f"{t('save_warning_hint', lang, id=row_id)}",
            parse_mode="HTML",
        )


link_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)
