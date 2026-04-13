import json
import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", TELEGRAM_TOKEN)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID", "")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
ENABLE_STARTUP_BACKFILL = (
    os.environ.get("ENABLE_STARTUP_BACKFILL", "false").strip().lower() == "true"
)


def get_google_credentials():
    return json.loads(GOOGLE_CREDENTIALS_JSON)


CATEGORIES = [
    "Tech",
    "FE",
    "UIUX",
    "Design",
    "Marketing",
    "Business",
    "Health",
    "Education",
    "Entertainment",
]

STATUS_VALUES = ["chua_doc", "dang_doc", "da_nghien_cuu", "da_ap_dung"]
PRIORITY_VALUES = ["high", "medium", "low"]
LIBRARY_GROUPS = [
    "animation",
    "shadcn",
    "icons",
    "charts",
    "forms",
    "table",
    "state-management",
    "utils",
]

SHEET_HEADERS = [
    "ID",
    "Ngay luu",
    "Tieu de",
    "Link goc",
    "Nguon",
    "Tom tat AI",
    "Ghi chu tay",
    "Chu de",
    "Tags",
    "Uu tien",
    "Trang thai",
    "Nguoi luu",
    "Thumbnail",
    "Library Group",
    "Nhac nho",
]
