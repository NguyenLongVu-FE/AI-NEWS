from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from bot.config import (
    ADMIN_TELEGRAM_ID,
    CATEGORIES,
    GOOGLE_SHEET_ID,
    PRIORITY_VALUES,
    STATUS_VALUES,
)
from bot.services.sheets import SheetsService
from bot.utils.formatting import format_view_detail, format_error

sheets = SheetsService()


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args or []) < 2:
        await update.message.reply_text(
            "❌ <b>Cu phap:</b> /status <i>ID</i> <i>trang thai</i>\n"
            f"Trang thai: {', '.join(STATUS_VALUES)}\n"
            "Vi du: /status 42 dang_doc",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("ID phai la so"), parse_mode="HTML"
        )
        return
    status = context.args[1].lower()
    if status not in STATUS_VALUES:
        await update.message.reply_text(
            format_error(
                f"Trang thai khong hop le. Dung: {', '.join(STATUS_VALUES)}",
                f"Vi du: /status {row_id} dang_doc",
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"Khong tim thay ID {row_id}"), parse_mode="HTML"
        )
        return
    old_status = record.get("Trang thai", "")
    sheets.update_cell(row_id, 11, status)
    await update.message.reply_text(
        f"✅ <b>Da cap nhat!</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"📌 Trang thai: {old_status} → {status}",
        parse_mode="HTML",
    )


async def note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args or []) < 2:
        await update.message.reply_text(
            "❌ <b>Cu phap:</b> /note <i>ID</i> <i>noi dung</i>\n"
            "Vi du: /note 42 Hay de tham khao",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("ID phai la so"), parse_mode="HTML"
        )
        return
    note_text = " ".join(context.args[1:])
    if len(note_text) > 500:
        await update.message.reply_text(
            format_error(
                f"Ghi chu qua dai ({len(note_text)}/500 ky tu)",
                "Rut gon ghi chu",
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"Khong tim thay ID {row_id}"), parse_mode="HTML"
        )
        return
    sheets.append_note(row_id, note_text)
    await update.message.reply_text(
        f"✅ <b>Da them ghi chu!</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"📝 {note_text}",
        parse_mode="HTML",
    )


async def priority_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args or []) < 2:
        await update.message.reply_text(
            f"❌ <b>Cu phap:</b> /priority <i>ID</i> <i>{'/'.join(PRIORITY_VALUES)}</i>\n"
            f"Vi du: /priority 42 high",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("ID phai la so"), parse_mode="HTML"
        )
        return
    priority = context.args[1].lower()
    if priority not in PRIORITY_VALUES:
        await update.message.reply_text(
            format_error(
                f"Uu tien khong hop le. Dung: {', '.join(PRIORITY_VALUES)}",
                f"Vi du: /priority {row_id} high",
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"Khong tim thay ID {row_id}"), parse_mode="HTML"
        )
        return
    sheets.update_cell(row_id, 10, priority)
    await update.message.reply_text(
        f"✅ <b>Da cap nhat uu tien!</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"🔴 Uu tien: {record.get('Uu tien', '')} → {priority}",
        parse_mode="HTML",
    )


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Cu phap:</b> /delete <i>ID</i>\nVi du: /delete 42",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("ID phai la so"), parse_mode="HTML"
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"Khong tim thay ID {row_id}"), parse_mode="HTML"
        )
        return
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Yes, Delete", callback_data=f"c:del:{row_id}:y"
                ),
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"v:{row_id}"
                ),
            ],
        ]
    )
    await update.message.reply_text(
        f"🗑️ <b>Xac nhan xoa</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"🔗 {record.get('Link goc', '')}\n\nBan co chac muon xoa?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def edit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args or []) < 3:
        await update.message.reply_text(
            "❌ <b>Cu phap:</b> /edit <i>ID</i> <i>field</i> <i>value</i>\n"
            "Fields: title, notes, category, tags\n"
            "Vi du: /edit 42 title Tieu de moi",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("ID phai la so"), parse_mode="HTML"
        )
        return
    field = context.args[1].lower()
    value = " ".join(context.args[2:])
    col_map = {"title": 3, "notes": 7, "category": 8, "tags": 9}
    if field not in col_map:
        await update.message.reply_text(
            format_error(
                f"Field khong hop le. Dung: {', '.join(col_map.keys())}"
            ),
            parse_mode="HTML",
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"Khong tim thay ID {row_id}"), parse_mode="HTML"
        )
        return
    sheets.update_cell(row_id, col_map[field], value)
    await update.message.reply_text(
        f"✅ <b>Da cap nhat!</b>\n\n📄 <b>{record.get('Tieu de', '')}</b>\n"
        f"✏️ {field}: → {value}",
        parse_mode="HTML",
    )


async def view_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Cu phap:</b> /view <i>ID</i>\nVi du: /view 42",
            parse_mode="HTML",
        )
        return
    try:
        row_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            format_error("ID phai la so"), parse_mode="HTML"
        )
        return
    record = sheets.get_row(row_id)
    if not record:
        await update.message.reply_text(
            format_error(f"Khong tim thay ID {row_id}"), parse_mode="HTML"
        )
        return
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✏️ Edit", callback_data=f"a:edit:{row_id}"
                ),
                InlineKeyboardButton(
                    "📌 Status", callback_data=f"a:status:{row_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔴 Priority", callback_data=f"a:priority:{row_id}"
                ),
                InlineKeyboardButton(
                    "🗑️ Delete", callback_data=f"a:del:{row_id}"
                ),
            ],
        ]
    )
    await update.message.reply_text(
        format_view_detail(record),
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def sheet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    await update.message.reply_text(
        f"📊 <b>Google Sheets:</b>\n{url}", parse_mode="HTML"
    )


async def addcategory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Cu phap:</b> /addcategory <i>ten</i>\n"
            "Vi du: /addcategory Science",
            parse_mode="HTML",
        )
        return
    user_id = str(update.message.from_user.id)
    if ADMIN_TELEGRAM_ID and user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text(
            "❌ Chi admin moi them duoc category.", parse_mode="HTML"
        )
        return
    new_cat = context.args[0].capitalize()
    if new_cat in CATEGORIES:
        await update.message.reply_text(
            f"🏷 Category '{new_cat}' da ton tai.", parse_mode="HTML"
        )
        return
    CATEGORIES.append(new_cat)
    await update.message.reply_text(
        f"✅ <b>Da them category:</b> {new_cat}\n"
        f"Danh sach hien tai: {', '.join(CATEGORIES)}",
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
