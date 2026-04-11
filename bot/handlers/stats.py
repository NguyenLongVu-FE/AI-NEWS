from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.services.stats import StatsService, emoji_bar
from bot.services.settings import SettingsService
from bot.services.i18n import t

stats_service = StatsService()
settings_service = SettingsService()


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = settings_service.get_user_settings(str(update.message.from_user.id))["language"]
    period = "week" if context.args and context.args[0].lower() == "week" else "month"
    period_label = t(f"stats_{period}", lang)

    stats = stats_service.get_stats(period)

    text = f"📊 <b>{t('stats_title', lang)} — {period_label}</b>\n\n"

    text += f"📋 {t('stats_total', lang)}: {stats['total']}\n"
    text += f"✅ {t('stats_read', lang)}: {stats['read']}\n"
    text += f"📭 {t('stats_unread', lang)}: {stats['unread']}\n\n"

    if stats["contributors"]:
        text += f"👥 <b>{t('stats_contributors', lang)}</b>\n"
        for name, count in stats["contributors"]:
            text += f"  ▸ {name}: {count}\n"
        text += "\n"

    if stats["categories"]:
        text += f"🏷 <b>{t('stats_categories', lang)}</b>\n"
        for cat, count in stats["categories"]:
            bar = emoji_bar(count, stats["total"])
            pct = round((count / stats["total"]) * 100) if stats["total"] else 0
            text += f"  {bar} {pct}% {cat} ({count})\n"
        text += "\n"

    if stats["sources"]:
        text += f"📡 <b>{t('stats_sources', lang)}</b>\n"
        for src, count in stats["sources"]:
            bar = emoji_bar(count, stats["total"])
            pct = round((count / stats["total"]) * 100) if stats["total"] else 0
            text += f"  {bar} {pct}% {src} ({count})\n"
        text += "\n"

    if stats["tags"]:
        text += f"🔖 <b>{t('stats_tags', lang)}</b>\n"
        for tag, count in stats["tags"]:
            text += f"  ▸ #{tag}: {count}\n"

    await update.message.reply_text(text[:4096], parse_mode="HTML")


stats_handler = CommandHandler("stats", stats_cmd)
