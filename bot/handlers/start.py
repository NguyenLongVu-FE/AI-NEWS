from telegram import Update
from telegram.ext import CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    first_name = user.first_name or "ban"
    text = (
        f"👋 Chao <b>{first_name}</b>!\n\n"
        f"Toi la <b>InfoSaver Bot</b> — giup ban luu va quan ly thong tin "
        f"tu TikTok, YouTube, Facebook, Web, Twitter/X.\n\n"
        f"<b>Cach dung:</b>\n"
        f"▸ Gui link → Bot tu dong luu + tom tat\n"
        f"▸ Gui link kem: <code>#tag !high @category ghi chu</code>\n"
        f"▸ Dung lenh de tim kiem, loc, quan ly\n\n"
        f"<b>Lenh chinh:</b>\n"
        f"/search <i>tu khoa</i> — Tim kiem\n"
        f"/filter <i>@category !priority</i> — Loc\n"
        f"/unread — Chua doc\n"
        f"/help — Tat ca lenh\n\n"
        f"Bat dau bang cach gui 1 link vao day! 🚀"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>InfoSaver Bot — Huong dan</b>\n\n"
        "<b>📝 Luu link:</b>\n"
        "▸ Gui link → Tu dong luu + tom tat AI\n"
        "▸ Kem: <code>#tag1 #tag2</code> | <code>!high</code> | "
        "<code>@tech</code> | <i>ghi chu</i>\n\n"
        "<b>🔍 Tim kiem & Loc:</b>\n"
        "/search <i>tu khoa</i> — Tim trong tieu de + tom tat\n"
        "/filter <i>@category !priority</i> — Loc ket hop\n"
        "/tags — Xem tat ca tags\n"
        "/unread — Noi dung chua doc\n"
        "/today — Hom nay\n"
        "/week — Tuan nay\n\n"
        "<b>⚙️ Quan ly:</b>\n"
        "/view <i>ID</i> — Xem chi tiet\n"
        "/status <i>ID</i> <i>trang thai</i> — Cap nhat trang thai\n"
        "/note <i>ID</i> <i>noi dung</i> — Them ghi chu\n"
        "/priority <i>ID</i> <i>level</i> — Doi uu tien\n"
        "/edit <i>ID</i> <i>field</i> <i>value</i> — Sua noi dung\n"
        "/delete <i>ID</i> — Xoa\n\n"
        "<b>📊 Khac:</b>\n"
        "/sheet — Link Google Sheets\n"
        "/addcategory <i>ten</i> — Them chu de (admin)"
    )
    await update.message.reply_text(text, parse_mode="HTML")


start_handler = CommandHandler("start", start)
help_handler = CommandHandler("help", help_command)
