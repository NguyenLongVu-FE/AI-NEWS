from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot.services.sheets import SheetsService
from bot.utils.formatting import format_view_detail, format_error

sheets = SheetsService()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("v:"):
        row_id = int(data[2:])
        await _handle_view(query, row_id)
    elif data.startswith("a:del:"):
        row_id = int(data[6:])
        await _handle_delete_confirm(query, row_id)
    elif data.startswith("c:del:"):
        parts = data.split(":")
        row_id = int(parts[2])
        confirmed = parts[3] == "y"
        await _handle_delete_execute(query, row_id, confirmed)
    elif data.startswith("a:status:"):
        row_id = int(data[9:])
        await _handle_status_menu(query, row_id)
    elif data.startswith("s:status:"):
        parts = data.split(":")
        row_id = int(parts[2])
        status = parts[3]
        await _handle_status_set(query, row_id, status)
    elif data.startswith("a:priority:"):
        row_id = int(data[11:])
        await _handle_priority_menu(query, row_id)
    elif data.startswith("s:priority:"):
        parts = data.split(":")
        row_id = int(parts[2])
        priority = parts[3]
        await _handle_priority_set(query, row_id, priority)


async def _handle_view(query, row_id):
    record = sheets.get_row(row_id)
    if not record:
        await query.edit_message_text(
            format_error(f"Khong tim thay ID {row_id}"), parse_mode="HTML"
        )
        return
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"a:edit:{row_id}"),
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
    await query.edit_message_text(
        format_view_detail(record), parse_mode="HTML", reply_markup=keyboard
    )


async def _handle_delete_confirm(query, row_id):
    record = sheets.get_row(row_id)
    title = record.get("Tieu de", "N/A") if record else "N/A"
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
    await query.edit_message_text(
        f"🗑️ <b>Xac nhan xoa</b>\n\n📄 <b>{title}</b>\n\n"
        f"Ban co chac muon xoa?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_delete_execute(query, row_id, confirmed):
    if confirmed:
        sheets.delete_row(row_id)
        await query.edit_message_text("✅ <b>Da xoa!</b>", parse_mode="HTML")
    else:
        await _handle_view(query, row_id)


async def _handle_status_menu(query, row_id):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📭 Chua doc",
                    callback_data=f"s:status:{row_id}:chua_doc",
                ),
                InlineKeyboardButton(
                    "📖 Dang doc",
                    callback_data=f"s:status:{row_id}:dang_doc",
                ),
            ],
            [
                InlineKeyboardButton(
                    "✅ Da nghien cuu",
                    callback_data=f"s:status:{row_id}:da_nghien_cuu",
                ),
                InlineKeyboardButton(
                    "🏆 Da ap dung",
                    callback_data=f"s:status:{row_id}:da_ap_dung",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"v:{row_id}"
                ),
            ],
        ]
    )
    await query.edit_message_text(
        "📌 <b>Chon trang thai moi:</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_status_set(query, row_id, status):
    sheets.update_cell(row_id, 11, status)
    await _handle_view(query, row_id)


async def _handle_priority_menu(query, row_id):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔴 High", callback_data=f"s:priority:{row_id}:high"
                ),
                InlineKeyboardButton(
                    "🟡 Medium",
                    callback_data=f"s:priority:{row_id}:medium",
                ),
                InlineKeyboardButton(
                    "🟢 Low", callback_data=f"s:priority:{row_id}:low"
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"v:{row_id}"
                ),
            ],
        ]
    )
    await query.edit_message_text(
        "🔴 <b>Chon uu tien moi:</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def _handle_priority_set(query, row_id, priority):
    sheets.update_cell(row_id, 10, priority)
    await _handle_view(query, row_id)


callback_handler = CallbackQueryHandler(handle_callback)
