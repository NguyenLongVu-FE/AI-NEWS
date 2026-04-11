import json
import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID", "")


def get_google_credentials():
    return json.loads(GOOGLE_CREDENTIALS_JSON)


CATEGORIES = [
    "Tech",
    "Business",
    "Design",
    "Marketing",
    "Health",
    "Education",
    "Entertainment",
    "Other",
]

STATUS_VALUES = ["chua_doc", "dang_doc", "da_nghien_cuu", "da_ap_dung"]
PRIORITY_VALUES = ["high", "medium", "low"]

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
    "Nhac nho",
]
