import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.services.reminder import ReminderService
from bot.config import TELEGRAM_BOT_TOKEN

from api.index import app

import httpx


@app.get("/cron/digest")
async def cron_digest():
    reminder = ReminderService()
    digests = reminder.get_all_digests()

    async with httpx.AsyncClient() as client:
        for d in digests:
            try:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": d["user_id"],
                        "text": d["message"],
                        "parse_mode": "HTML",
                    },
                )
            except Exception:
                pass

    return {"sent": len(digests), "total_users": len(digests)}
