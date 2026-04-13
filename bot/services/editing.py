import re
from typing import Any

from bot.config import SHEET_HEADERS
from bot.services.category import is_forbidden_other_category, normalize_category_name
from bot.services.i18n import t
from bot.services.keywords import normalize_keywords

EDIT_FIELD_ALIASES = {"tags": "keywords"}
EDITABLE_FIELDS = ("title", "notes", "category", "keywords")
EDIT_FIELD_COLUMN = {
    "title": 3,
    "notes": 7,
    "category": 8,
    "keywords": SHEET_HEADERS.index("Tags") + 1,
}


def normalize_edit_field(field: str) -> str:
    key = str(field or "").strip().lower()
    return EDIT_FIELD_ALIASES.get(key, key)


def normalize_keywords_input(value: str) -> str:
    raw = str(value or "").replace("\n", " ")
    parts = [part.lstrip("#") for part in re.split(r"[,\s]+", raw) if part.strip()]
    return ", ".join(normalize_keywords(parts))


def apply_record_edit(sheets, row_id: int, field: str, value: str, lang: str = "vi") -> dict[str, Any]:
    normalized_field = normalize_edit_field(field)
    if normalized_field not in EDITABLE_FIELDS:
        return {
            "ok": False,
            "error": t("field_invalid", lang, values=", ".join(EDITABLE_FIELDS)),
            "clear_pending": False,
        }

    record = sheets.get_row_by_id(row_id)
    if not record:
        return {
            "ok": False,
            "error": f"{t('not_found', lang)} {row_id}",
            "clear_pending": True,
        }

    value_to_save = str(value or "").strip()
    if not value_to_save:
        return {
            "ok": False,
            "error": t("edit_value_required", lang),
            "clear_pending": False,
        }

    if normalized_field == "category":
        if is_forbidden_other_category(value_to_save):
            return {
                "ok": False,
                "error": t("category_other_forbidden", lang),
                "clear_pending": False,
            }
        value_to_save = normalize_category_name(value_to_save) or value_to_save
        if not sheets.move_row_to_topic_by_id(row_id, value_to_save):
            return {
                "ok": False,
                "error": f"{t('not_found', lang)} {row_id}",
                "clear_pending": True,
            }
    elif normalized_field == "keywords":
        value_to_save = normalize_keywords_input(value_to_save)
        if not value_to_save:
            return {
                "ok": False,
                "error": t("edit_value_required", lang),
                "clear_pending": False,
            }
        if not sheets.update_cell_by_id(row_id, EDIT_FIELD_COLUMN[normalized_field], value_to_save):
            return {
                "ok": False,
                "error": f"{t('not_found', lang)} {row_id}",
                "clear_pending": True,
            }
    else:
        if not sheets.update_cell_by_id(row_id, EDIT_FIELD_COLUMN[normalized_field], value_to_save):
            return {
                "ok": False,
                "error": f"{t('not_found', lang)} {row_id}",
                "clear_pending": True,
            }

    updated_record = sheets.get_row_by_id(row_id) or record
    return {
        "ok": True,
        "field": normalized_field,
        "value": value_to_save,
        "record": updated_record,
        "clear_pending": True,
    }
