# BRIEF - InfoSaver Bot (Updated)

## 1. Tổng quan sản phẩm

**Tên:** InfoSaver Bot

**Mô tả:** Telegram Bot giúp cá nhân/nhóm nhỏ (2-5 người) lưu trữ, phân loại, tóm tắt và quản lý thông tin/news từ nhiều nguồn khác nhau (TikTok, YouTube, Facebook, Web/Blog, Twitter/X). Mọi dữ liệu được đồng bộ vào Google Sheets để dễ lọc, nghiên cứu và không bị trôi nội dung.

---

## 2. Kiến trúc hệ thống

```
[User] --> [Telegram Bot] --> [Vercel Serverless (FastAPI)]
                                        |
                        +---------------+---------------+
                        |               |               |
                [Google Gemini AI] [Google Sheets API] [Vercel Cron]
                        |               |               |
                (Tóm tắt nội dung) (Lưu trữ)    (Nhắc nhở + Backup)
```

### Tech Stack (Updated)

| Thành phần | Công nghệ |
|---|---|
| **Bot Platform** | Telegram Bot API (webhook mode) |
| **Web Framework** | FastAPI (Vercel serverless) |
| **Bot Library** | python-telegram-bot |
| **AI Tóm tắt** | Google Gemini 2.5 Flash |
| **Lưu trữ** | Google Sheets API (gspread) |
| **Web Scraping** | BeautifulSoup4 + requests |
| **Scheduler** | Vercel Cron Jobs |
| **Deploy** | Vercel (free tier, serverless) |
| **CI/CD** | GitHub → Vercel auto-deploy |

---

## 3. Phases & Context Files

### Phase 1 - MVP
**Context:** `.planning/phases/01-infosaver-bot/01-CONTEXT.md` (31 decisions)

- Telegram Bot nhận link (FastAPI webhook)
- Google Sheets 14 columns (A-N)
- AI tóm tắt Gemini (async: reply ngay → xử lý sau)
- Phân loại: tags, priority, category
- Tìm kiếm: /search, /filter, /tags, /unread, /today, /week
- Quản lý: /status, /note, /priority, /delete, /edit, /view, /sheet, /addcategory
- Duplicate detection + auto-split Sheets
- Source detection (URL pattern matching)

### Phase 2 - Full Features
**Context:** `.planning/phases/02-full-features/02-CONTEXT.md` (17 decisions)

- Reminder: daily digest 8:00 AM, /remind on/off, auto Sheets highlighting
- Song ngữ VI/EN (bot UI only, AI summary luôn tiếng Việt)
- Export Excel (.xlsx) qua Telegram
- /stats: top contributor, popular categories, overview, source breakdown (emoji bars)

### Phase 3 - Deploy & Production
**Context:** `.planning/phases/03-deploy-production/03-CONTEXT.md` (16 decisions)

- Vercel free tier + webhook mode
- Security: Vercel env vars, basic input validation, weekly auto-export backup
- Monitoring: Vercel dashboard + Telegram admin alerts
- CI/CD: GitHub auto-deploy, AI-assisted updates, Vercel instant rollback

### Phase 4 - Tương lai (Deferred)
- Browser Extension
- Web Dashboard
- Mobile App
- Notion / Obsidian integration

---

## 4. Commands Telegram Bot (Full List)

### Lệnh cơ bản (Phase 1)
| Command | Mô tả |
|---|---|
| `/start` | Khởi động bot, hướng dẫn sử dụng |
| `/help` | Hiển thị tất cả lệnh |

### Lệnh lưu & quản lý (Phase 1)
| Command | Mô tả |
|---|---|
| `<link>` | Gửi link nhanh, bot tự xử lý (async) |
| `<link> + ghi chú` | Gửi link kèm #tags !priority @category ghi chú |
| `/status <ID> <trạng thái>` | Cập nhật: chua_doc/dang_doc/da_nghien_cuu/da_ap_dung |
| `/note <ID> <nội dung>` | Thêm ghi chú cho link đã lưu |
| `/priority <ID> <high/medium/low>` | Đổi mức ưu tiên |
| `/delete <ID>` | Xóa link (có xác nhận) |
| `/edit <ID> <field> <value>` | Sửa: title, notes, category, tags |
| `/view <ID>` | Xem chi tiết 1 link |
| `/sheet` | Gửi link Google Sheets |
| `/addcategory <name>` | Thêm category mới (admin only) |

### Lệnh tìm kiếm & lọc (Phase 1)
| Command | Mô tả |
|---|---|
| `/search <từ khóa>` | Tìm trong tiêu đề + tóm tắt + tags (keyword matching) |
| `/filter [@chủ đề] [!priority]` | Lọc kết hợp: /filter @tech !high |
| `/tags` | Xem tất cả tags đang có |
| `/unread` | Nội dung chưa đọc |
| `/today` | Nội dung hôm nay |
| `/week` | Nội dung tuần này |

### Lệnh nâng cao (Phase 2)
| Command | Mô tả |
|---|---|
| `/lang vi` hoặc `/lang en` | Chuyển ngôn ngữ bot UI |
| `/remind <ID> <số ngày>` | Đặt nhắc nhở |
| `/remind on/off` | Bật/tắt daily digest |
| `/export` | Xuất Excel (.xlsx) qua Telegram |
| `/stats` | Thống kê tháng này |
| `/stats week` | Thống kê tuần này |

### Lệnh thư viện UI (Task 6)
| Command | Mô tả |
|---|---|
| `/lib` | Hiển thị danh sách nhóm thư viện và số lượng theo từng nhóm |
| `/lib <group>` | Lọc nhanh dữ liệu theo nhóm thư viện trong chat |
| `/lib sheet <group>` | Tạo/cập nhật mirror sheet theo nhóm và chạy backfill từ main sheet |

- Mirror sheets đặt tên cố định: `LIB_animation`, `LIB_shadcn`, `LIB_icons`, `LIB_charts`, `LIB_forms`, `LIB_table`, `LIB_state-management`, `LIB_utils`.
- Main sheet là source of truth; các `LIB_<group>` là mirror sheets theo nhóm.
- Nếu mirror sync bị drift/fail, chạy `/lib sheet <group>` để re-backfill từ source.

---

## 5. Giao diện Song ngữ (Phase 2)

Bot hỗ trợ cả tiếng Việt và tiếng Anh. Mặc định tiếng Việt, chuyển bằng `/lang en`.

**AI Summary luôn tiếng Việt** bất kể user chọn ngôn ngữ nào. Bot UI (thông báo, help, responses) theo ngôn ngữ user chọn.

---

## 6. Chi phí ước tính (Updated)

| Dịch vụ | Chi phí/tháng |
|---|---|
| Google Gemini 2.5 Flash | ~$1-3 |
| Google Sheets API | Miễn phí |
| Telegram Bot API | Miễn phí |
| Vercel (Hobby free tier) | $0 |
| **Tổng** | **~$1-3/tháng** |

---

## 7. Setup (Phase 1 + Phase 3)

### Bước cần chuẩn bị:
1. **Telegram Bot Token** → Chat với @BotFather trên Telegram
2. **Google Service Account** → Tạo tại Google Cloud Console, enable Sheets API
3. **Google Gemini API Key** → Lấy tại Google AI Studio
4. **GitHub Account** → Để push code và auto-deploy
5. **Vercel Account** → Free, kết nối với GitHub

### Setup flow:
1. Clone repo
2. Tạo `.env` từ `.env.example` (điền API keys)
3. Tạo Google Sheets + share cho Service Account
4. Push lên GitHub → Vercel auto-deploy
5. Set webhook URL cho Telegram bot
6. README hướng dẫn từng bước chi tiết

---

## 8. Ghi chú quan trọng

- **User không biết code** → Toàn bộ codebase vibe code. Setup qua README, update qua AI
- **API keys** → Vercel Environment Variables (encrypted)
- **Google Sheets** → Share cho Service Account email
- **Backup** → Weekly auto-export Excel gửi qua Telegram (Phase 3)
- **Rate limit** Gemini Flash: 15 RPM free tier, đủ dùng cá nhân
- **Vercel timeout** 10s → async processing: reply ngay, xử lý sau
- **Debug** → Log file + gửi cho AI phân tích

---

## 9. Context Files Index

| File | Phase | Decisions | Status |
|---|---|---|---|
| `.planning/phases/01-infosaver-bot/01-CONTEXT.md` | MVP | 31 decisions | Ready for planning |
| `.planning/phases/01-infosaver-bot/01-DISCUSSION-LOG.md` | MVP | Audit trail | Complete |
| `.planning/phases/02-full-features/02-CONTEXT.md` | Full Features | 17 decisions | Ready for planning |
| `.planning/phases/02-full-features/02-03-DISCUSSION-LOG.md` | Phase 2+3 | Audit trail | Complete |
| `.planning/phases/03-deploy-production/03-CONTEXT.md` | Deploy | 16 decisions | Ready for planning |
