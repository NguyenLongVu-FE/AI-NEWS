PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_DISPLAY = {
    "chua_doc": "📭 Chua doc",
    "dang_doc": "📖 Dang doc",
    "da_nghien_cuu": "✅ Da nghien cuu",
    "da_ap_dung": "🏆 Da ap dung",
}


def format_save_success(title, source, category, priority, ai_summary, row_id):
    p_emoji = PRIORITY_EMOJI.get(priority, "🟡")
    summary_display = ai_summary[:200] + "..." if len(ai_summary) > 200 else ai_summary
    return (
        f"✅ <b>Da luu thanh cong!</b>\n\n"
        f"📄 <b>Tieu de:</b> {title}\n"
        f"🔗 <b>Nguon:</b> {source}\n"
        f"🏷 <b>Chu de:</b> {category} | Uu tien: {p_emoji} {priority}\n"
        f"🤖 <b>Tom tat AI:</b> {summary_display}\n\n"
        f"ID: <code>{row_id}</code>"
    )


def format_processing():
    return "⏳ <b>Dang xu ly...</b>\n\nAI dang tom tat noi dung."


def format_error(message: str, suggestion: str = ""):
    text = f"❌ <b>Loi</b>\n\n{message}"
    if suggestion:
        text += f"\n\n💡 <b>Goi y:</b> {suggestion}"
    return text


def format_empty_state(context_msg: str):
    return (
        f"📭 <b>Khong tim thay noi dung</b>\n\n"
        f"{context_msg}\n\n"
        f"💡 <b>Goi y:</b>\n"
        f"▸ /search <i>tu khoa khac</i>\n"
        f"▸ /filter de loc theo chu de"
    )


def format_view_detail(record: dict):
    p_emoji = PRIORITY_EMOJI.get(record.get("Uu tien", ""), "🟡")
    status_display = STATUS_DISPLAY.get(
        record.get("Trang thai", ""), record.get("Trang thai", "")
    )
    return (
        f"📄 <b>{record.get('Tieu de', 'N/A')}</b>\n"
        f"─────────\n"
        f"🔗 <b>Link:</b> <a href=\"{record.get('Link goc', '')}\">"
        f"{record.get('Link goc', '')[:50]}</a>\n"
        f"📡 <b>Nguon:</b> {record.get('Nguon', 'N/A')}\n"
        f"🏷 <b>Chu de:</b> {record.get('Chu de', 'N/A')}\n"
        f"🏷 <b>Tags:</b> {record.get('Tags', 'N/A')}\n"
        f"{p_emoji} <b>Uu tien:</b> {record.get('Uu tien', 'N/A')}\n"
        f"📌 <b>Trang thai:</b> {status_display}\n"
        f"👤 <b>Luu boi:</b> {record.get('Nguoi luu', 'N/A')}\n\n"
        f"<b>🤖 Tom tat AI:</b>\n"
        f"<blockquote>{record.get('Tom tat AI', 'Chua co')}</blockquote>\n\n"
        f"<b>📝 Ghi chu:</b>\n"
        f"{record.get('Ghi chu tay', 'Chua co ghi chu')}\n\n"
        f"ID: <code>{record.get('ID', 'N/A')}</code>"
    )
