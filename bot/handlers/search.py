from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.sheets import get_sheets_service
from bot.services.settings import SettingsService
from bot.services.i18n import t
from bot.utils.formatting import format_empty_state

PAGE_SIZE = 5
settings_service = SettingsService()


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return settings_service.get_user_settings(user_id)["language"]


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    if not context.args:
        await update.message.reply_text(
            f"❌ <b>{t('search_syntax', lang)}</b> /search <i>{t('search_keyword_placeholder', lang)}</i>\n"
            f"{t('search_example', lang)}",
            parse_mode="HTML",
        )
        return
    sheets = get_sheets_service()
    keyword = " ".join(context.args)
    results = sheets.search(keyword)
    await _send_results(
        update, results, f'{t("search_label", lang)}: "{keyword}"', lang
    )


async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    category = ""
    keyword = ""
    for arg in context.args or []:
        if arg.startswith("@"):
            category = arg[1:]
        elif arg.startswith("#"):
            keyword = arg[1:]
    sheets = get_sheets_service()
    results = sheets.filter_by(category=category or None, keyword=keyword or None)
    label = (
        f"{t('filter_label', lang)}: {f'@{category}' if category else ''} "
        f"{f'#{keyword}' if keyword else ''}"
    ).strip()
    await _send_results(update, results, label, lang)


async def tags_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    sheets = get_sheets_service()
    records = sheets.get_all_records()
    all_tags = set()
    for r in records:
        tag_str = r.get("Tags", "")
        if tag_str:
            for tg in tag_str.split(","):
                tg = tg.strip()
                if tg:
                    all_tags.add(tg)
    if not all_tags:
        await update.message.reply_text(
            format_empty_state(t("no_tags", lang), lang=lang),
            parse_mode="HTML",
        )
        return
    tag_list = sorted(all_tags)
    text = f"🏷 <b>{t('tags_title', lang)}</b>\n\n" + "\n".join(
        f"▸ <code>{tg}</code>" for tg in tag_list
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    sheets = get_sheets_service()
    records = sheets.get_all_records()
    today_str = datetime.now().strftime("%Y-%m-%d")
    results = [
        r for r in records if str(r.get("Ngay luu", "")).startswith(today_str)
    ]
    await _send_results(update, results, t("today_label", lang), lang)


async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    sheets = get_sheets_service()
    records = sheets.get_all_records()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    results = [
        r
        for r in records
        if str(r.get("Ngay luu", ""))[:10] >= week_ago
    ]
    await _send_results(update, results, t("week_label", lang), lang)


async def _send_results(update: Update, results, label: str, lang: str):
    if not results:
        await update.message.reply_text(
            format_empty_state(t("no_content_for", lang, label=label), lang=lang),
            parse_mode="HTML",
        )
        return
    page = results[:PAGE_SIZE]
    text = f"🔍 <b>{label}</b>\n{t('search_results', lang)} {len(results)} {t('results', lang)}:\n\n"
    for i, r in enumerate(page, 1):
        title = r.get("Tieu de", "N/A")
        source = r.get("Nguon", "N/A")
        cat = r.get("Chu de", "N/A")
        keywords = r.get("Tags", "")
        summary = r.get("Tom tat AI", "")[:100]
        rid = r.get("ID", "")
        text += (
            f"<b>{i}.</b> {title}\n"
            f"🔗 {source} | 🏷 {cat}\n"
            f"🔖 {keywords}\n"
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
                InlineKeyboardButton(f"◀️ {t('prev_label', lang)}", callback_data="p:srch:1"),
                InlineKeyboardButton(f"{t('next_label', lang)} ▶️", callback_data="p:srch:2"),
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
today_handler = CommandHandler("today", today)
week_handler = CommandHandler("week", week)
