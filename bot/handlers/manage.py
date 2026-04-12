from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from bot.config import (
    ADMIN_TELEGRAM_ID,
    CATEGORIES,
    GOOGLE_SHEET_ID,
    PRIORITY_VALUES,
    STATUS_VALUES,
)
from bot.services.sheets import get_sheets_service
from bot.services.settings import SettingsService
from bot.services.i18n import t
from bot.utils.formatting import format_view_detail, format_error

settings_service = SettingsService()


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


def _example(lang: str, command: str) -> str:
    return f"{t('example_prefix', lang)}: {command}"


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    lang = _get_lang(update)
    if len(context.args or []) < 2:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /status <i>ID</i> <i>{t('status_label', lang)}</i>\n"
            f"{t('status_label', lang)}: {', '.join(STATUS_VALUES)}\n"
            f"{_example(lang, '/status 42 dang_doc')}",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error(t("id_must_be_number", lang), lang=lang), parse_mode="HTML"
        )
        return
    status = context.args[1].lower()
    if status not in STATUS_VALUES:
        await update.message.reply_text(
            format_error(
                t("status_invalid", lang, values=", ".join(STATUS_VALUES)),
                _example(lang, f"/status {row_id} dang_doc"),
                lang=lang,
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    old_status = record.get("Trang thai", "")
    sheets.update_cell(row_id, 11, status)
    await update.message.reply_text(
        f"✅ <b>{t('status_updated', lang)}</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"📌 {t('status_label', lang)}: {old_status} → {status}",
        parse_mode="HTML",
    )


async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    lang = _get_lang(update)
    if len(context.args or []) < 2:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /note <i>ID</i> <i>content</i>\n"
            f"{_example(lang, '/note 42 Add context')}",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error(t("id_must_be_number", lang), lang=lang), parse_mode="HTML"
        )
        return
    note_text = " ".join(context.args[1:])
    if len(note_text) > 500:
        await update.message.reply_text(
            format_error(
                t("note_too_long", lang, current=len(note_text), max=500),
                t("note_shorten_hint", lang),
                lang=lang,
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    sheets.append_note(row_id, note_text)
    await update.message.reply_text(
        f"✅ <b>{t('note_added', lang)}</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"📝 {note_text}",
        parse_mode="HTML",
    )


async def priority_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    lang = _get_lang(update)
    if len(context.args or []) < 2:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /priority <i>ID</i> <i>{'/'.join(PRIORITY_VALUES)}</i>\n"
            f"{_example(lang, '/priority 42 high')}",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error(t("id_must_be_number", lang), lang=lang), parse_mode="HTML"
        )
        return
    priority = context.args[1].lower()
    if priority not in PRIORITY_VALUES:
        await update.message.reply_text(
            format_error(
                t("priority_invalid", lang, values=", ".join(PRIORITY_VALUES)),
                _example(lang, f"/priority {row_id} high"),
                lang=lang,
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    sheets.update_cell(row_id, 10, priority)
    await update.message.reply_text(
        f"✅ <b>{t('priority_updated', lang)}</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"🔴 {t('priority_label', lang)}: {record.get('Uu tien', '')} → {priority}",
        parse_mode="HTML",
    )


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    lang = _get_lang(update)
    if not context.args:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /delete <i>ID</i>\n{_example(lang, '/delete 42')}",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error(t("id_must_be_number", lang), lang=lang), parse_mode="HTML"
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
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
    await update.message.reply_text(
        f"🗑️ <b>{t('delete_confirm', lang)}</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"🔗 {record.get('Link goc', '')}\n\n{t('delete_confirm_msg', lang)}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def edit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    lang = _get_lang(update)
    if len(context.args or []) < 3:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /edit <i>ID</i> <i>field</i> <i>value</i>\n"
            f"{t('fields_label', lang)}: title, notes, category, tags\n"
            f"{_example(lang, '/edit 42 title New title')}",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error(t("id_must_be_number", lang), lang=lang), parse_mode="HTML"
        )
        return
    field = context.args[1].lower()
    value = " ".join(context.args[2:])
    col_map = {"title": 3, "notes": 7, "category": 8, "tags": 9}
    if field not in col_map:
        await update.message.reply_text(
            format_error(
                t("field_invalid", lang, values=", ".join(col_map.keys())),
                lang=lang,
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    sheets.update_cell(row_id, col_map[field], value)
    await update.message.reply_text(
        f"✅ <b>{t('edit_updated', lang)}</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"✏️ {field}: → {value}",
        parse_mode="HTML",
    )


async def view_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    lang = _get_lang(update)
    if not context.args:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /view <i>ID</i>\n{_example(lang, '/view 42')}",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error(t("id_must_be_number", lang), lang=lang), parse_mode="HTML"
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("edit_button", lang), callback_data=f"a:edit:{row_id}"
                ),
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
    await update.message.reply_text(
        format_view_detail(record, lang=lang),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def sheet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    await update.message.reply_text(
        f"📊 <b>{t('sheet_title', lang)}</b>\n{url}", parse_mode="HTML"
    )


async def addcategory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    if not context.args:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /addcategory <i>name</i>\n"
            f"{_example(lang, '/addcategory Science')}",
            parse_mode="HTML",
        )
        return
    user_id = str(update.message.from_user.id)
    if ADMIN_TELEGRAM_ID and user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text(
            f"❌ {t('admin_only', lang)}", parse_mode="HTML"
        )
        return
    new_cat = context.args[0].capitalize()
    if new_cat in CATEGORIES:
        await update.message.reply_text(
            f"🏷 {new_cat} {t('category_exists', lang)}.",
            parse_mode="HTML",
        )
        return
    CATEGORIES.append(new_cat)
    await update.message.reply_text(
        f"✅ <b>{t('category_added', lang)}</b> {new_cat}\n"
        f"{t('category_list', lang)}: {', '.join(CATEGORIES)}",
        parse_mode="HTML",
    )


status_handler = CommandHandler("status", status_cmd)
note_handler = CommandHandler("note", note_cmd)
priority_handler = CommandHandler("priority", priority_cmd)
delete_handler = CommandHandler("delete", delete_cmd)
edit_handler = CommandHandler("edit", edit_cmd)
view_handler = CommandHandler("view", view_cmd)
sheet_handler = CommandHandler("sheet", sheet_cmd)
addcategory_handler = CommandHandler("addcategory", addcategory_cmd)
