import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application

from bot.config import TELEGRAM_BOT_TOKEN

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

_initialized = False


@app.post("/webhook")
async def webhook(request: Request):
    global _initialized
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
