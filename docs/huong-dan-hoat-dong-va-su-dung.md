# Hướng dẫn hoạt động và sử dụng InfoSaver Bot

## 1. Ứng dụng dùng để làm gì

InfoSaver Bot là Telegram bot giúp lưu link (TikTok, YouTube, Facebook, Web, Twitter/X), tự lấy metadata, tóm tắt bằng AI, rồi lưu toàn bộ vào Google Sheets để tìm kiếm, lọc và quản lý.

---

## 2. Ứng dụng hoạt động như thế nào

### Luồng tổng quát

1. Người dùng gửi tin nhắn chứa URL vào Telegram.
2. Telegram gọi webhook của ứng dụng (`/webhook` hoặc đường dẫn deploy tương đương `/api/webhook`).
3. Bot phân tích nội dung tin nhắn:
   - URL
   - `#tag`
   - `!priority` (`high|medium|low`)
   - `@category`
   - `~library_group` (ghi đè nhóm thư viện)
   - phần text còn lại là ghi chú.
4. Bot kiểm tra URL hợp lệ, kiểm tra số lượng tag.
5. Bot xử lý nội dung:
   - Scrape title/description/thumbnail từ trang.
   - Tóm tắt AI bằng Gemini 2.5 Flash.
   - Xác định nguồn (TikTok/YouTube/Facebook/Twitter/X/Web).
   - Xác định `Library Group` (ưu tiên `~group`, nếu không có thì auto detect).
6. Bot lưu dữ liệu vào sheet chính (main sheet).
7. Bot đồng bộ bản ghi sang sheet mirror theo nhóm `LIB_<group>`.
8. Bot phản hồi trong Telegram kèm ID để quản lý tiếp.

### Xử lý link trùng

- Nếu URL đã tồn tại, bot **không tạo dòng mới**.
- Nếu có ghi chú mới, bot gộp thêm vào cột ghi chú của bản ghi cũ.

### Daily digest và backup`

- Cron chạy:
  - `0 1 * * *` → digest hằng ngày (01:00 UTC, ~08:00 ICT).
  - `0 2 * * 1` → backup hằng tuần (02:00 UTC thứ Hai, ~09:00 ICT).
- Digest gửi cho user đang bật nhắc nhở (`/remind on`) khi có:
  - link `high` chưa đọc quá 3 ngày, hoặc
  - link `dang_doc` quá 7 ngày.
- Backup gửi file `.xlsx` cho admin.

---

## 3. Cấu trúc dữ liệu chính (Google Sheets)

Sheet chính dùng các cột:

`ID, Ngay luu, Tieu de, Link goc, Nguon, Tom tat AI, Ghi chu tay, Chu de, Tags, Uu tien, Trang thai, Nguoi luu, Thumbnail, Library Group, Nhac nho`

Mirror sheet theo nhóm:

- `LIB_animation`
- `LIB_shadcn`
- `LIB_icons`
- `LIB_charts`
- `LIB_forms`
- `LIB_table`
- `LIB_state-management`
- `LIB_utils`

---

## 4. Cách sử dụng trong Telegram

### 4.1 Gửi link để lưu

Ví dụ:

```text
https://ui.shadcn.com/docs/components/button #ui #react !high @tech ~shadcn cần áp dụng cho project A
```

Quy ước:

- `#...` là tag
- `!...` là độ ưu tiên (`high|medium|low`)
- `@...` là category
- `~...` là library group (nếu muốn tự chỉ định)
- phần còn lại là ghi chú

### 4.2 Danh sách lệnh

| Nhóm | Lệnh | Mô tả |
|---|---|---|
| Cơ bản | `/start`, `/help` | Bắt đầu và xem hướng dẫn |
| Tìm kiếm/lọc | `/search <keyword>` | Tìm theo tiêu đề/tóm tắt/tags |
|  | `/filter @category !priority` | Lọc theo category và priority |
|  | `/tags` | Xem danh sách tags |
|  | `/unread`, `/today`, `/week` | Lọc nhanh theo trạng thái/thời gian |
| Quản lý bản ghi | `/view <ID>` | Xem chi tiết |
|  | `/status <ID> <chua_doc/dang_doc/da_nghien_cuu/da_ap_dung>` | Đổi trạng thái |
|  | `/priority <ID> <high/medium/low>` | Đổi ưu tiên |
|  | `/note <ID> <noi_dung>` | Thêm ghi chú |
|  | `/edit <ID> <field> <value>` | Sửa trường (`title`, `notes`, `category`, `tags`, `library_group`) |
|  | `/delete <ID>` | Xóa bản ghi (có xác nhận) |
| Sheet | `/sheet` | Lấy link Google Sheets |
| Ngôn ngữ | `/lang vi`, `/lang en` | Đổi ngôn ngữ UI bot |
| Nhắc nhở | `/remind on`, `/remind off` | Bật/tắt daily digest |
| Xuất dữ liệu | `/export` | Xuất file Excel |
| Thống kê | `/stats`, `/stats week` | Thống kê tháng/tuần |
| Thư viện UI | `/lib` | Xem số lượng theo library group |
|  | `/lib <group>` | Xem nhanh dữ liệu theo group |
|  | `/lib sheet <group>` | Tạo/cập nhật mirror sheet theo group |
| Admin | `/addcategory <name>` | Thêm category (chỉ admin) |

---

## 5. Cài đặt và chạy

### 5.1 Biến môi trường

Thiết lập đủ 7 biến sau:

- `TELEGRAM_TOKEN`
- `TELEGRAM_BOT_TOKEN` (đặt cùng giá trị với `TELEGRAM_TOKEN`)
- `GEMINI_API_KEY`
- `GOOGLE_CREDENTIALS_JSON` (JSON service account một dòng)
- `GOOGLE_SHEET_ID`
- `TELEGRAM_WEBHOOK_SECRET`
- `ADMIN_TELEGRAM_ID`

### 5.2 Chạy local

```bash
pip install -r requirements.txt
pip install uvicorn
python -m uvicorn api.index:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

### 5.3 Deploy Vercel + webhook Telegram

Webhook mẫu:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<your-domain>/api/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Kiểm tra deploy:

```bash
python scripts/deploy_checks.py --base-url "https://<your-domain>"
```

---

## 6. API endpoint chính

- `POST /webhook` — nhận update từ Telegram
- `GET /health` — health endpoint
- `GET /cron/digest` và `GET /api/cron/digest` — chạy gửi digest
- `GET /cron/backup` và `GET /api/cron/backup` — chạy backup tuần

---

## 7. Lưu ý vận hành

- Nếu bật `TELEGRAM_WEBHOOK_SECRET`, request sai secret sẽ trả `{"ok": false, "error": "unauthorized"}`.
- Khi lỗi HTTP tăng đột biến (>=5 lỗi trong 10 phút), hệ thống gửi cảnh báo cho admin Telegram.
- Nếu mirror sheet bị lệch dữ liệu, chạy lại `/lib sheet <group>` để backfill từ sheet chính.
