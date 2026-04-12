import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from fastapi import APIRouter

from bot.config import ADMIN_TELEGRAM_ID, TELEGRAM_BOT_TOKEN
from bot.services.export import ExportService
from bot.services.reminder import ReminderService

router = APIRouter()


@router.get("/cron/digest")
@router.get("/api/cron/digest")
async def cron_digest():
    reminder = ReminderService()
    digests = reminder.get_all_digests()
    sent = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        for d in digests:
            try:
                response = await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": d["user_id"],
                        "text": d["message"],
                        "parse_mode": "HTML",
                    },
                )
                if response.is_success:
                    sent += 1
                else:
                    failed += 1
            except httpx.HTTPError:
                failed += 1

    return {"sent": sent, "failed": failed, "total_users": len(digests)}


@router.get("/cron/backup")
@router.get("/api/cron/backup")
async def cron_backup():
    if not ADMIN_TELEGRAM_ID:
        return {"sent": False, "reason": "admin_not_configured"}

    export_service = ExportService()
    xlsx_data = export_service.generate_xlsx()
    filename = f"infosaver-weekly-backup-{datetime.now().strftime('%Y%m%d')}.xlsx"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
            data={
                "chat_id": ADMIN_TELEGRAM_ID,
                "caption": "📦 Weekly InfoSaver backup",
                "parse_mode": "HTML",
            },
            files={
                "document": (
                    filename,
                    xlsx_data,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    if response.is_success:
        return {"sent": True, "filename": filename}

    return {
        "sent": False,
        "filename": filename,
        "status_code": response.status_code,
    }
