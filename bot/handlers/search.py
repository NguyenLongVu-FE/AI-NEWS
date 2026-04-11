from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.sheets import get_sheets_service
from bot.utils.formatting import format_empty_state

PAGE_SIZE = 5


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Cu phap:</b> /search <i>tu khoa</i>\n"
            "Vi du: /search python",
            parse_mode="HTML",
        )
        return
    sheets = get_sheets_service()
    keyword = " ".join(context.args)
    results = sheets.search(keyword)
    await _send_results(update, results, f'Tim kiem: "{keyword}"')


async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = ""
    priority = ""
    for arg in context.args or []:
        if arg.startswith("@"):
            category = arg[1:]
        elif arg.startswith("!"):
            priority = arg[1:].lower()
    sheets = get_sheets_service()
    results = sheets.filter_by(category=category or None, priority=priority or None)
    label = (
        f"Loc: {f'@{category}' if category else ''} "
        f"{f'!{priority}' if priority else ''}"
    ).strip()
    await _send_results(update, results, label)


async def tags_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    records = sheets.get_all_records()
    all_tags = set()
    for r in records:
        tag_str = r.get("Tags", "")
        if tag_str:
            for t in tag_str.split(","):
                t = t.strip()
                if t:
                    all_tags.add(t)
    if not all_tags:
        await update.message.reply_text(
            format_empty_state(
                "Chua co tags nao. Them tags bang # khi gui link."
            ),
            parse_mode="HTML",
        )
        return
    tag_list = sorted(all_tags)
    text = "🏷 <b>Tat ca tags:</b>\n\n" + "\n".join(
        f"▸ <code>{t}</code>" for t in tag_list
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def unread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    results = sheets.filter_by(status="chua_doc")
    await _send_results(update, results, "Chua doc")


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    records = sheets.get_all_records()
    today_str = datetime.now().strftime("%Y-%m-%d")
    results = [
        r for r in records if str(r.get("Ngay luu", "")).startswith(today_str)
    ]
    await _send_results(update, results, "Hom nay")


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sheets = get_sheets_service()
    records = sheets.get_all_records()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    results = [
        r
        for r in records
        if str(r.get("Ngay luu", ""))[:10] >= week_ago
    ]
    await _send_results(update, results, "Tuan nay")


async def _send_results(update, results, label):
    if not results:
        await update.message.reply_text(
            format_empty_state(f"Khong co noi dung cho: {label}"),
            parse_mode="HTML",
        )
        return
    page = results[:PAGE_SIZE]
    text = f"🔍 <b>{label}</b>\nTim thay {len(results)} ket qua:\n\n"
    for i, r in enumerate(page, 1):
        title = r.get("Tieu de", "N/A")
        source = r.get("Nguon", "N/A")
        cat = r.get("Chu de", "N/A")
        summary = r.get("Tom tat AI", "")[:100]
        rid = r.get("ID", "")
        text += (
            f"<b>{i}.</b> {title}\n"
            f"🔗 {source} | 🏷 {cat}\n"
            f"<blockquote>{summary}</blockquote>\n\n"
        )
    buttons = [
        [
            InlineKeyboardButton(
                f"👁 #{r.get('ID', '')}",
                callback_data=f"v:{r.get('ID')}",
            )
            for r in page[:5]
        ]
    ]
    if len(results) > PAGE_SIZE:
        buttons.append(
            [
                InlineKeyboardButton("◀️ 1/2", callback_data="p:srch:1"),
                InlineKeyboardButton("Next ▶️", callback_data="p:srch:2"),
            ]
        )
    await update.message.reply_text(
        text[:4096],
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


search_handler = CommandHandler("search", search)
filter_handler = CommandHandler("filter", filter_cmd)
tags_handler = CommandHandler("tags", tags_cmd)
unread_handler = CommandHandler("unread", unread)
today_handler = CommandHandler("today", today)
week_handler = CommandHandler("week", week)
