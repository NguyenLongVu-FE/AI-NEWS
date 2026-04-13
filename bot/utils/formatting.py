from bot.services.i18n import t

def format_save_success(title, source, category, ai_summary, row_id, lang: str = "vi"):
    summary_display = ai_summary[:200] + "..." if len(ai_summary) > 200 else ai_summary
    return (
        f"✅ <b>{t('save_success', lang)}</b>\n\n"
        f"📄 <b>{t('save_title', lang)}</b> {title}\n"
        f"🔗 <b>{t('save_source', lang)}</b> {source}\n"
        f"🏷 <b>{t('save_category', lang)}</b> {category}\n"
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
        f"▸ /filter <i>@topic #keyword</i>"
    )


def format_view_detail(record: dict, lang: str = "vi"):
    return (
        f"📄 <b>{record.get('Tieu de', 'N/A')}</b>\n"
        f"─────────\n"
        f"🔗 <b>{t('saved_link_label', lang)}</b> <a href=\"{record.get('Link goc', '')}\">"
        f"{record.get('Link goc', '')[:50]}</a>\n"
        f"📡 <b>{t('save_source', lang)}</b> {record.get('Nguon', 'N/A')}\n"
        f"🏷 <b>{t('save_category', lang)}</b> {record.get('Chu de', 'N/A')}\n"
        f"🏷 <b>{t('keywords_label', lang)}</b> {record.get('Tags', 'N/A')}\n"
        f"👤 <b>{t('saved_by_label', lang)}</b> {record.get('Nguoi luu', 'N/A')}\n\n"
        f"<b>🤖 {t('save_ai_summary', lang)}</b>\n"
        f"<blockquote>{record.get('Tom tat AI', t('no_summary', lang))}</blockquote>\n\n"
        f"<b>📝 {t('notes_label', lang)}</b>\n"
        f"{record.get('Ghi chu tay', t('no_note', lang))}\n\n"
        f"ID: <code>{record.get('ID', 'N/A')}</code>"
    )
