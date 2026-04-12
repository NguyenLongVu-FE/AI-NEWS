import os
import sys
import time
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application

from bot.config import TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET, ADMIN_TELEGRAM_ID

app = FastAPI()

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

from bot.handlers.start import start_handler, help_handler
from bot.handlers.link import link_handler
from bot.handlers.search import (
    search_handler,
    filter_handler,
    tags_handler,
    unread_handler,
    today_handler,
    week_handler,
)
from bot.handlers.manage import (
    status_handler,
    note_handler,
    priority_handler,
    delete_handler,
    edit_handler,
    view_handler,
    sheet_handler,
    addcategory_handler,
)
from bot.handlers.callback import callback_handler
from bot.handlers.lang import lang_handler
from bot.handlers.export import export_handler
from bot.handlers.stats import stats_handler
from bot.handlers.remind import remind_handler
from api.cron import router as cron_router

application.add_handler(start_handler)
application.add_handler(help_handler)
application.add_handler(link_handler)
application.add_handler(search_handler)
application.add_handler(filter_handler)
application.add_handler(tags_handler)
application.add_handler(unread_handler)
application.add_handler(today_handler)
application.add_handler(week_handler)
application.add_handler(status_handler)
application.add_handler(note_handler)
application.add_handler(priority_handler)
application.add_handler(delete_handler)
application.add_handler(edit_handler)
application.add_handler(view_handler)
application.add_handler(sheet_handler)
application.add_handler(addcategory_handler)
application.add_handler(callback_handler)
application.add_handler(lang_handler)
application.add_handler(export_handler)
application.add_handler(stats_handler)
application.add_handler(remind_handler)

app.include_router(cron_router)

_initialized = False
_error_timestamps = deque(maxlen=100)
ERROR_ALERT_THRESHOLD = 5
ERROR_ALERT_WINDOW = 600


async def _send_admin_alert(error_msg: str):
    if not ADMIN_TELEGRAM_ID:
        return
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": ADMIN_TELEGRAM_ID,
                    "text": f"⚠️ <b>Bot Alert</b>\n\n{error_msg}\n\nCheck Vercel dashboard for details.",
                    "parse_mode": "HTML",
                },
            )
        except Exception:
            pass


@app.middleware("http")
async def error_monitor(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        now = time.time()
        _error_timestamps.append(now)

        recent_errors = sum(
            1 for ts in _error_timestamps if now - ts < ERROR_ALERT_WINDOW
        )

        if recent_errors >= ERROR_ALERT_THRESHOLD:
            alert_msg = f"{recent_errors} errors in last 10 min. Latest: {str(e)[:200]}"
            await _send_admin_alert(alert_msg)
            _error_timestamps.clear()

        raise e


@app.post("/webhook")
async def webhook(request: Request):
    global _initialized

    if TELEGRAM_WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret != TELEGRAM_WEBHOOK_SECRET:
            return {"ok": False, "error": "unauthorized"}

    if not _initialized:
        await application.initialize()
        _initialized = True
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok", "initialized": _initialized}
