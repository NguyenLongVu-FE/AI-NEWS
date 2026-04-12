import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot.services.sheets import get_sheets_service
from bot.services.settings import SettingsService
from bot.services.i18n import t
from bot.services.library_groups import normalize_library_group
from bot.utils.formatting import format_view_detail, format_error

settings_service = SettingsService()
logger = logging.getLogger(__name__)


def _get_lang(query) -> str:
    user_id = str(query.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


def _get_record_by_id(sheets, row_id: int):
    if hasattr(sheets, "get_row_by_id"):
        return sheets.get_row_by_id(row_id)
    return sheets.get_row(row_id)


def _delete_row_by_id(sheets, row_id: int) -> bool:
    if hasattr(sheets, "delete_row_by_id"):
        return sheets.delete_row_by_id(row_id)
    sheets.delete_row(row_id)
    return True


def _update_cell_by_id(sheets, row_id: int, col: int, value: str) -> bool:
    if hasattr(sheets, "update_cell_by_id"):
        return sheets.update_cell_by_id(row_id, col, value)
    sheets.update_cell(row_id, col, value)
    return True


def _sync_library_mirror(sheets, row_id: int):
    updated_record = _get_record_by_id(sheets, row_id)
    if not updated_record:
        logger.warning(
            "Mirror sync skipped for row_id=%s: record not found after update", row_id
        )
        return

    try:
        sheets.upsert_library_row(updated_record)
    except Exception:
        logger.warning("Mirror upsert failed for row_id=%s", row_id, exc_info=True)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    sheets = get_sheets_service()
    lang = _get_lang(query)

    if data.startswith("v:"):
        row_id = int(data[2:])
        await _handle_view(query, row_id, sheets, lang)
    elif data.startswith("a:del:"):
        row_id = int(data[6:])
        await _handle_delete_confirm(query, row_id, sheets, lang)
    elif data.startswith("c:del:"):
        parts = data.split(":")
        row_id = int(parts[2])
        confirmed = parts[3] == "y"
        await _handle_delete_execute(query, row_id, confirmed, sheets, lang)
    elif data.startswith("a:status:"):
        row_id = int(data[9:])
        await _handle_status_menu(query, row_id, lang)
    elif data.startswith("s:status:"):
        parts = data.split(":")
        row_id = int(parts[2])
        status = parts[3]
        await _handle_status_set(query, row_id, status, sheets, lang)
    elif data.startswith("a:priority:"):
        row_id = int(data[11:])
        await _handle_priority_menu(query, row_id, lang)
    elif data.startswith("s:priority:"):
        parts = data.split(":")
        row_id = int(parts[2])
        priority = parts[3]
        await _handle_priority_set(query, row_id, priority, sheets, lang)


async def _handle_view(query, row_id, sheets, lang: str):
    record = _get_record_by_id(sheets, row_id)
    if not record:
        await query.edit_message_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("edit_button", lang), callback_data=f"a:edit:{row_id}"),
                InlineKeyboardButton(
                    t("status_button", lang), callback_data=f"a:status:{row_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    t("priority_button", lang), callback_data=f"a:priority:{row_id}"
                ),
                InlineKeyboardButton(
                    t("delete_button", lang), callback_data=f"a:del:{row_id}"
                ),
            ],
        ]
    )
    await query.edit_message_text(
        format_view_detail(record, lang=lang), parse_mode="HTML", reply_markup=keyboard
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
        record = _get_record_by_id(sheets, row_id)
        if not _delete_row_by_id(sheets, row_id):
            await query.edit_message_text(
                format_error(f"{t('not_found', lang)} {row_id}", lang=lang),
                parse_mode="HTML",
            )
            return
        if record:
            record_id = str(record.get("ID", "")).strip() or str(row_id)
            record_group = normalize_library_group(record.get("Library Group")) or "utils"
            try:
                sheets.remove_library_row(record_id, record_group)
            except Exception:
                logger.warning(
                    "Mirror cleanup failed for deleted row_id=%s in group=%s",
                    row_id,
                    record_group,
                    exc_info=True,
                )
        await query.edit_message_text(f"✅ <b>{t('deleted', lang)}</b>", parse_mode="HTML")
    else:
        await _handle_view(query, row_id, sheets, lang)


async def _handle_status_menu(query, row_id, lang: str):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("status_chua_doc", lang),
                    callback_data=f"s:status:{row_id}:chua_doc",
                ),
                InlineKeyboardButton(
                    t("status_dang_doc", lang),
                    callback_data=f"s:status:{row_id}:dang_doc",
                ),
            ],
            [
                InlineKeyboardButton(
                    t("status_da_nghien_cuu", lang),
                    callback_data=f"s:status:{row_id}:da_nghien_cuu",
                ),
                InlineKeyboardButton(
                    t("status_da_ap_dung", lang),
                    callback_data=f"s:status:{row_id}:da_ap_dung",
                ),
            ],
            [
                InlineKeyboardButton(
                    t("cancel", lang), callback_data=f"v:{row_id}"
                ),
            ],
        ]
    )
    await query.edit_message_text(
        t("choose_new_status", lang),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_status_set(query, row_id, status, sheets, lang: str):
    if not _update_cell_by_id(sheets, row_id, 11, status):
        await query.edit_message_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang),
            parse_mode="HTML",
        )
        return
    _sync_library_mirror(sheets, row_id)
    await _handle_view(query, row_id, sheets, lang)


async def _handle_priority_menu(query, row_id, lang: str):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"🔴 {t('priority_high_text', lang)}",
                    callback_data=f"s:priority:{row_id}:high",
                ),
                InlineKeyboardButton(
                    f"🟡 {t('priority_medium_text', lang)}",
                    callback_data=f"s:priority:{row_id}:medium",
                ),
                InlineKeyboardButton(
                    f"🟢 {t('priority_low_text', lang)}",
                    callback_data=f"s:priority:{row_id}:low",
                ),
            ],
            [
                InlineKeyboardButton(
                    t("cancel", lang), callback_data=f"v:{row_id}"
                ),
            ],
        ]
    )
    await query.edit_message_text(
        t("choose_new_priority", lang),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_priority_set(query, row_id, priority, sheets, lang: str):
    if not _update_cell_by_id(sheets, row_id, 10, priority):
        await query.edit_message_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang),
            parse_mode="HTML",
        )
        return
    _sync_library_mirror(sheets, row_id)
    await _handle_view(query, row_id, sheets, lang)


callback_handler = CallbackQueryHandler(handle_callback)
