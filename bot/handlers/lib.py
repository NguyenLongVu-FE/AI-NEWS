from html import escape

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.config import LIBRARY_GROUPS, SHEET_HEADERS, SHEET_DISPLAY_HEADERS
from bot.services.i18n import t
from bot.services.library_groups import normalize_library_group
from bot.services.settings import SettingsService
from bot.services.sheets import get_sheets_service
from bot.utils.formatting import format_error

MAX_PREVIEW_ITEMS = 8

_settings_service = None


def _get_settings_service() -> SettingsService:
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service


def _get_lang(update: Update) -> str:
    user_id = str(update.message.from_user.id)
    return _get_settings_service().get_user_settings(user_id)["language"]


def _count_groups(records: list[dict]) -> dict[str, int]:
    counts = {group: 0 for group in LIBRARY_GROUPS}
    for record in records:
        counts[_normalize_record_group(record)] += 1
    return counts


def _normalize_record_group(record: dict) -> str:
    raw_group = str(record.get("Library Group", "")).strip()
    return normalize_library_group(raw_group) or "utils"


def _filter_records_by_group(records: list[dict], group: str) -> list[dict]:
    return [record for record in records if _normalize_record_group(record) == group]


def _record_to_sheet_row(record: dict) -> list[str]:
    row_record = dict(record)
    row_record["Library Group"] = _normalize_record_group(record)
    return [row_record.get(header, "") for header in SHEET_HEADERS]


def _group_preview(results: list[dict]) -> str:
    lines = []
    for record in results[:MAX_PREVIEW_ITEMS]:
        row_id = escape(str(record.get("ID", "")).strip() or "?")
        title = escape(str(record.get("Tieu de", "N/A")).strip() or "N/A")
        source = escape(str(record.get("Nguon", "")).strip())
        if source:
            lines.append(f"• <code>#{row_id}</code> {title} — {source}")
        else:
            lines.append(f"• <code>#{row_id}</code> {title}")
    return "\n".join(lines)


async def _reply_invalid_group(update: Update, lang: str, group_value: str):
    group_text = escape(str(group_value or "").strip()) or "?"
    await update.message.reply_text(
        format_error(
            t("lib_invalid_group", lang, group=group_text),
            t("lib_valid_groups", lang, groups=", ".join(LIBRARY_GROUPS)),
            lang=lang,
        ),
        parse_mode="HTML",
    )


async def _list_library_groups(update: Update, lang: str):
    sheets = get_sheets_service()
    records = sheets.get_all_records()
    counts = _count_groups(records)

    rows = "\n".join(f"• <code>{group}</code>: {counts[group]}" for group in LIBRARY_GROUPS)
    text = (
        f"📚 <b>{t('lib_groups_title', lang)}</b>\n"
        f"{t('stats_total', lang)}: <b>{len(records)}</b>\n\n"
        f"{rows}\n\n"
        f"{t('lib_usage', lang)}"
    )
    await update.message.reply_text(text[:4096], parse_mode="HTML")


async def _show_group_results(update: Update, lang: str, group_value: str):
    group = normalize_library_group(group_value)
    if not group:
        await _reply_invalid_group(update, lang, group_value)
        return

    sheets = get_sheets_service()
    results = _filter_records_by_group(sheets.get_all_records(), group)

    if not results:
        await update.message.reply_text(
            (
                f"📚 <b>{t('lib_group_title', lang, group=group)}</b>\n"
                f"{t('search_results', lang)} <b>0</b> {t('results', lang)}\n\n"
                f"{t('lib_group_empty', lang, group=group)}"
            ),
            parse_mode="HTML",
        )
        return

    remaining = len(results) - min(len(results), MAX_PREVIEW_ITEMS)
    more_line = (
        f"\n\n{t('lib_group_more', lang, count=remaining)}" if remaining > 0 else ""
    )
    text = (
        f"📚 <b>{t('lib_group_title', lang, group=group)}</b>\n"
        f"{t('search_results', lang)} <b>{len(results)}</b> {t('results', lang)}\n\n"
        f"{_group_preview(results)}{more_line}"
    )
    await update.message.reply_text(text[:4096], parse_mode="HTML")


async def _ensure_group_sheet(update: Update, lang: str, args: list[str]):
    if not args:
        await update.message.reply_text(
            format_error(
                t("search_syntax", lang),
                t("lib_sheet_usage", lang),
                lang=lang,
            ),
            parse_mode="HTML",
        )
        return

    group = normalize_library_group(args[0])
    if not group:
        await _reply_invalid_group(update, lang, args[0])
        return

    sheets = get_sheets_service()
    source_records = _filter_records_by_group(sheets.get_all_records(), group)
    mirror_sheet = sheets.ensure_library_sheet(group)
    mirror_records = mirror_sheet.get_all_records()

    source_ids = {
        str(record.get("ID", "")).strip()
        for record in source_records
        if str(record.get("ID", "")).strip()
    }
    removed = sum(
        1
        for mirror_record in mirror_records
        if (mirror_id := str(mirror_record.get("ID", "")).strip())
        and mirror_id not in source_ids
    )

    source_rows = [_record_to_sheet_row(record) for record in source_records]
    mirror_sheet.update(
        range_name="A1",
        values=[SHEET_DISPLAY_HEADERS, *source_rows],
        value_input_option="RAW",
    )
    if len(mirror_records) > len(source_rows):
        mirror_sheet.delete_rows(len(source_rows) + 2, len(mirror_records) + 1)

    sheet_name = escape(getattr(mirror_sheet, "title", f"LIB_{group}"))
    text = (
        f"✅ <b>{t('lib_sheet_done', lang, sheet=sheet_name)}</b>\n"
        f"{t('lib_sheet_stats', lang, backfilled=len(source_records), removed=removed)}\n"
        f"{t('lib_sheet_hint', lang, group=group)}"
    )
    await update.message.reply_text(text[:4096], parse_mode="HTML")


async def lib_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _get_lang(update)
    args = [arg.strip() for arg in context.args or [] if arg.strip()]

    if not args:
        await _list_library_groups(update, lang)
        return

    if args[0].lower() == "sheet":
        await _ensure_group_sheet(update, lang, args[1:])
        return

    await _show_group_results(update, lang, args[0])


lib_handler = CommandHandler("lib", lib_cmd)
