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
    "AI Agent",
    "FE",
    "UIUX",
    "Design",
    "Marketing",
    "Business",
    "Health",
    "Education",
    "Entertainment",
]

TOPIC_SHEET_PREFIX = "TOPIC_"

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
    "Nguoi luu",
    "Thumbnail",
]

SHEET_DISPLAY_HEADERS = [
    "ID",
    "Ngày lưu",
    "Tiêu đề",
    "Link gốc",
    "Nguồn",
    "Tóm tắt AI",
    "Ghi chú tay",
    "Chủ đề",
    "Từ khóa",
    "Người lưu",
    "Thumbnail",
]
