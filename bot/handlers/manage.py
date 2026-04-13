from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from bot.config import ADMIN_TELEGRAM_ID, CATEGORIES, GOOGLE_SHEET_ID
from bot.services.category import is_forbidden_other_category, normalize_category_name
from bot.services.editing import EDITABLE_FIELDS, apply_record_edit
from bot.services.i18n import t
from bot.services.settings import SettingsService
from bot.services.sheets import get_sheets_service
from bot.utils.formatting import format_error, format_view_detail

settings_service = SettingsService()


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


def _example(lang: str, command: str) -> str:
    return f"{t('example_prefix', lang)}: {command}"


def _get_record_by_id(sheets, row_id: int):
    return sheets.get_row_by_id(row_id)


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
    record = _get_record_by_id(sheets, row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    if not sheets.append_note_by_id(row_id, note_text):
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return
    await update.message.reply_text(
        f"✅ <b>{t('note_added', lang)}</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"📝 {note_text}",
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
    record = _get_record_by_id(sheets, row_id)
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
            f"{t('fields_label', lang)}: {', '.join(EDITABLE_FIELDS)}\n"
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
    record = _get_record_by_id(sheets, row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"{t('not_found', lang)} {row_id}", lang=lang), parse_mode="HTML"
        )
        return

    result = apply_record_edit(sheets, row_id=row_id, field=field, value=value, lang=lang)
    if not result["ok"]:
        await update.message.reply_text(
            format_error(result["error"], lang=lang),
            parse_mode="HTML",
        )
        return

    await update.message.reply_text(
        f"✅ <b>{t('edit_updated', lang)}</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"✏️ {result['field']}: → {result['value']}",
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
    record = _get_record_by_id(sheets, row_id)
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
            f"{_example(lang, '/addcategory AI Agent')}",
            parse_mode="HTML",
        )
        return
    user_id = str(update.message.from_user.id)
    if ADMIN_TELEGRAM_ID and user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text(
            f"❌ {t('admin_only', lang)}", parse_mode="HTML"
        )
        return
    new_cat_raw = " ".join(context.args).strip()
    if is_forbidden_other_category(new_cat_raw):
        await update.message.reply_text(
            format_error(t("category_other_forbidden", lang), lang=lang),
            parse_mode="HTML",
        )
        return
    new_cat = normalize_category_name(new_cat_raw) or new_cat_raw
    if any(category.lower() == new_cat.lower() for category in CATEGORIES):
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


note_handler = CommandHandler("note", note_cmd)
delete_handler = CommandHandler("delete", delete_cmd)
edit_handler = CommandHandler("edit", edit_cmd)
view_handler = CommandHandler("view", view_cmd)
sheet_handler = CommandHandler("sheet", sheet_cmd)
addcategory_handler = CommandHandler("addcategory", addcategory_cmd)
