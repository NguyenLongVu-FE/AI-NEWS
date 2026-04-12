from bot.services.i18n import t

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_KEY_MAP = {
    "chua_doc": "status_chua_doc",
    "dang_doc": "status_dang_doc",
    "da_nghien_cuu": "status_da_nghien_cuu",
    "da_ap_dung": "status_da_ap_dung",
}


def format_save_success(title, source, category, priority, ai_summary, row_id, lang: str = "vi"):
    p_emoji = PRIORITY_EMOJI.get(priority, "🟡")
    summary_display = ai_summary[:200] + "..." if len(ai_summary) > 200 else ai_summary
    return (
        f"✅ <b>{t('save_success', lang)}</b>\n\n"
        f"📄 <b>{t('save_title', lang)}</b> {title}\n"
        f"🔗 <b>{t('save_source', lang)}</b> {source}\n"
        f"🏷 <b>{t('save_category', lang)}</b> {category} | {t('priority_label', lang)} {p_emoji} {priority}\n"
        f"🤖 <b>{t('save_ai_summary', lang)}</b> {summary_display}\n\n"
        f"ID: <code>{row_id}</code>"
    )


def format_processing(lang: str = "vi"):
    return f"⏳ <b>{t('processing', lang)}</b>\n\n{t('processing_desc', lang)}"


def format_error(message: str, suggestion: str = "", lang: str = "vi"):
    text = f"❌ <b>{t('error', lang)}</b>\n\n{message}"
    if suggestion:
        text += f"\n\n💡 <b>{t('suggestion', lang)}</b> {suggestion}"
    return text


def format_empty_state(context_msg: str, lang: str = "vi"):
    return (
        f"📭 <b>{t('empty_state', lang)}</b>\n\n"
        f"{context_msg}\n\n"
        f"💡 <b>{t('suggestion', lang)}</b>\n"
        f"▸ /search <i>{t('search_keyword_placeholder', lang)}</i>\n"
        f"▸ /filter <i>@category !priority</i>"
    )


def format_view_detail(record: dict, lang: str = "vi"):
    p_emoji = PRIORITY_EMOJI.get(record.get("Uu tien", ""), "🟡")
    status_key = STATUS_KEY_MAP.get(record.get("Trang thai", ""), "")
    status_display = t(status_key, lang) if status_key else record.get("Trang thai", "")
    return (
        f"📄 <b>{record.get('Tieu de', 'N/A')}</b>\n"
        f"─────────\n"
        f"🔗 <b>{t('saved_link_label', lang)}</b> <a href=\"{record.get('Link goc', '')}\">"
        f"{record.get('Link goc', '')[:50]}</a>\n"
        f"📡 <b>{t('save_source', lang)}</b> {record.get('Nguon', 'N/A')}\n"
        f"🏷 <b>{t('save_category', lang)}</b> {record.get('Chu de', 'N/A')}\n"
        f"🏷 <b>{t('tags_label', lang)}</b> {record.get('Tags', 'N/A')}\n"
        f"{p_emoji} <b>{t('priority_label', lang)}</b> {record.get('Uu tien', 'N/A')}\n"
        f"📌 <b>{t('status_label', lang)}</b> {status_display}\n"
        f"👤 <b>{t('saved_by_label', lang)}</b> {record.get('Nguoi luu', 'N/A')}\n\n"
        f"<b>🤖 {t('save_ai_summary', lang)}</b>\n"
        f"<blockquote>{record.get('Tom tat AI', t('no_summary', lang))}</blockquote>\n\n"
        f"<b>📝 {t('notes_label', lang)}</b>\n"
        f"{record.get('Ghi chu tay', t('no_note', lang))}\n\n"
        f"ID: <code>{record.get('ID', 'N/A')}</code>"
    )
