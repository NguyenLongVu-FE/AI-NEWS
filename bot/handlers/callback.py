from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot.services.editing import EDITABLE_FIELDS, normalize_edit_field
from bot.services.i18n import t
from bot.services.settings import SettingsService
from bot.services.sheets import get_sheets_service
from bot.utils.formatting import format_error, format_view_detail

settings_service = SettingsService()
_FIELD_LABEL_KEY = {
    "title": "edit_field_title",
    "notes": "edit_field_notes",
    "category": "edit_field_category",
    "keywords": "edit_field_keywords",
}


def _get_lang(query) -> str:
    user_id = str(query.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


def _get_record_by_id(sheets, row_id: int):
    return sheets.get_row_by_id(row_id)


def _detail_keyboard(row_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("edit_button", lang), callback_data=f"a:edit:{row_id}"),
                InlineKeyboardButton(
                    t("delete_button", lang), callback_data=f"a:del:{row_id}"
                ),
            ],
        ]
    )


def _edit_field_label(field: str, lang: str) -> str:
    return t(_FIELD_LABEL_KEY.get(field, "fields_label"), lang)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    sheets = get_sheets_service()
    lang = _get_lang(query)

    if data.startswith("v:"):
        row_id = int(data[2:])
        await _handle_view(query, row_id, sheets, lang)
    elif data.startswith("a:edit:"):
        row_id = int(data[7:])
        await _handle_edit_menu(query, row_id, sheets, lang)
    elif data.startswith("e:set:"):
        parts = data.split(":")
        row_id = int(parts[2])
        field = parts[3]
        await _handle_edit_set(query, row_id, field, sheets, lang, context)
    elif data.startswith("e:cancel:"):
        row_id = int(data.split(":")[2])
        await _handle_edit_cancel(query, row_id, sheets, lang, context)
    elif data.startswith("a:del:"):
        row_id = int(data[6:])
        await _handle_delete_confirm(query, row_id, sheets, lang)
    elif data.startswith("c:del:"):
        parts = data.split(":")
        row_id = int(parts[2])
        confirmed = parts[3] == "y"
        await _handle_delete_execute(query, row_id, confirmed, sheets, lang)


async def _handle_view(query, row_id, sheets, lang: str):
    record = _get_record_by_id(sheets, row_id)
    if not record:
        await query.edit_message_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    await query.edit_message_text(
        format_view_detail(record, lang=lang),
        parse_mode="HTML",
        reply_markup=_detail_keyboard(row_id, lang),
    )


async def _handle_edit_menu(query, row_id, sheets, lang: str):
    if not _get_record_by_id(sheets, row_id):
        await query.edit_message_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"📝 {_edit_field_label('title', lang)}",
                    callback_data=f"e:set:{row_id}:title",
                ),
                InlineKeyboardButton(
                    f"🗒 {_edit_field_label('notes', lang)}",
                    callback_data=f"e:set:{row_id}:notes",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"🏷 {_edit_field_label('category', lang)}",
                    callback_data=f"e:set:{row_id}:category",
                ),
                InlineKeyboardButton(
                    f"🔖 {_edit_field_label('keywords', lang)}",
                    callback_data=f"e:set:{row_id}:keywords",
                ),
            ],
            [
                InlineKeyboardButton(
                    t("cancel", lang),
                    callback_data=f"v:{row_id}",
                ),
            ],
        ]
    )
    await query.edit_message_text(
        t("edit_choose_field", lang, id=row_id),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_edit_set(query, row_id, field, sheets, lang: str, context: ContextTypes.DEFAULT_TYPE):
    normalized_field = normalize_edit_field(field)
    if normalized_field not in EDITABLE_FIELDS:
        await query.edit_message_text(
            format_error(
                t("field_invalid", lang, values=", ".join(EDITABLE_FIELDS)),
                lang=lang,
            ),
            parse_mode="HTML",
        )
        return
    if not _get_record_by_id(sheets, row_id):
        await query.edit_message_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return

    context.user_data["pending_edit"] = {"row_id": row_id, "field": normalized_field}
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("cancel", lang),
                    callback_data=f"e:cancel:{row_id}",
                ),
            ],
        ]
    )
    await query.edit_message_text(
        t(
            "edit_input_prompt",
            lang,
            id=row_id,
            field=_edit_field_label(normalized_field, lang),
        ),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_edit_cancel(query, row_id, sheets, lang: str, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_edit", None)
    if _get_record_by_id(sheets, row_id):
        await _handle_view(query, row_id, sheets, lang)
        return
    await query.edit_message_text(
        f"ℹ️ {t('edit_cancelled', lang)}",
        parse_mode="HTML",
    )


async def _handle_delete_confirm(query, row_id, sheets, lang: str):
    record = _get_record_by_id(sheets, row_id)
    title = record.get("Tieu de", "N/A") if record else "N/A"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("delete_yes", lang), callback_data=f"c:del:{row_id}:y"
                ),
                InlineKeyboardButton(
                    t("cancel", lang), callback_data=f"v:{row_id}"
                ),
            ],
        ]
    )
    await query.edit_message_text(
        f"🗑️ <b>{t('delete_confirm', lang)}</b>\n\n📄 <b>{title}</b>\n\n"
        f"{t('delete_confirm_msg', lang)}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_delete_execute(query, row_id, confirmed, sheets, lang: str):
    if confirmed:
        if not sheets.delete_row_by_id(row_id):
            await query.edit_message_text(
                format_error(f"{t('not_found', lang)} {row_id}", lang=lang),
                parse_mode="HTML",
            )
            return
        await query.edit_message_text(
            f"✅ <b>{t('deleted', lang)}</b>", parse_mode="HTML"
        )
    else:
        await _handle_view(query, row_id, sheets, lang)


callback_handler = CallbackQueryHandler(handle_callback)
