# Project: Telegram Money Bot (quản lý thu chi cá nhân)

## Trạng thái dự án

**Dự án mới, chưa có code.** Thư mục hiện đang trống. Mục "Cấu trúc thư mục" bên dưới là **kiến trúc dự kiến** để scaffold — khi bắt đầu code, tạo theo đúng cấu trúc này.

Dự án trước đây trong thư mục này (app Java Swing quản lý user, MySQL) đã bị xoá hoàn toàn theo yêu cầu người dùng — không còn liên quan, không cần giữ tương thích ngược với nó.

## 1. Tổng quan

Bot Telegram quản lý thu chi cá nhân — **1 người dùng, không phân biệt user/chat**. Gõ lệnh trực tiếp trong Telegram để cộng/trừ tiền, xem số dư và lịch sử giao dịch.

## 1b. Access control

Bot chạy polling công khai — để tránh người khác gõ lệnh vào dữ liệu tài chính cá nhân, mọi handler chỉ phản hồi khi `update.effective_chat.id == ALLOWED_CHAT_ID` (lấy từ `.env`, không hard-code). Đây là access-control, **không phải** multi-user support — bảng `transactions` vẫn không có cột `chat_id` (xem mục 7).

## 2. Tech stack

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.11+ |
| Bot framework | `python-telegram-bot` v21, **polling mode**, handler là `async def` |
| Lưu trữ | SQLite (`data/money.db`), tự tạo schema khi khởi động |
| Config | `.env` (token bot) qua `python-dotenv` |

## 3. Cấu trúc thư mục (dự kiến)

```
src/
├── bot.py        # entry point, đăng ký command handler, parse tham số lệnh
└── storage.py     # SQLite: init schema, add_transaction, get_balance, get_history
data/
└── money.db        # tự tạo khi chạy lần đầu, KHÔNG commit (đã có trong .gitignore)
.env.example         # copy thành .env, điền TELEGRAM_BOT_TOKEN
requirements.txt
```

## 4. Lệnh bot

| Lệnh | Cú pháp | Chức năng |
|---|---|---|
| `/start` | | Hướng dẫn dùng bot |
| `/help` | | Xem lại danh sách lệnh (nội dung giống `/start`) |
| `/cong` | `/cong <số tiền> [ghi chú]` | Cộng tiền, vd `/cong 50000 an sang` |
| `/tru` | `/tru <số tiền> [ghi chú]` | Trừ tiền, vd `/tru 20000 gui xe` |
| `/so` | | Xem số dư hiện tại |
| `/ls` | `/ls [ngày\|tháng/năm\|năm]` | Xem lịch sử giao dịch, mặc định 10 giao dịch gần nhất; lọc theo ngày (`22/09/2026`), tháng (`09/2026`) hoặc năm (`2026`) |
| `/thongke` | `/thongke [ngày\|tháng/năm\|năm]` | Tổng tiền cộng, tổng tiền trừ và chênh lệch theo khoảng thời gian; không truyền gì = toàn bộ lịch sử |
| `/trungbinh` | `/trungbinh [ngày\|tháng/năm\|năm]` | Trung bình cộng/trừ mỗi ngày; tháng/năm hiện tại (chưa kết thúc) tính theo số ngày đã trôi qua, không tính cả kỳ |
| `/top` | `/top [n] [ngày\|tháng/năm\|năm]` | n khoản chi (trừ) lớn nhất trong khoảng lọc, mặc định n=5, vd `/top 5 09/2026` |

Bảng `transactions`: `id, amount (INTEGER, âm = trừ), note, created_at`. Số dư = `SUM(amount)`.

## 5. Chạy project

```bash
pip install -r requirements.txt
cp .env.example .env   # rồi điền TELEGRAM_BOT_TOKEN (từ @BotFather) và ALLOWED_CHAT_ID (chat cá nhân)
python src/bot.py
```

## 6. Quy ước (đã chốt — không tự ý đổi khi không được yêu cầu)

- Text phản hồi cho người dùng viết bằng **tiếng Việt**.
- **Số tiền luôn là số nguyên VNĐ.** Mọi dấu `.` hoặc `,` trong input đều bị strip vô điều kiện trước khi parse (`50.000` và `50,000` đều = 50000) — không cố hỗ trợ số thập phân.
- **Số dưới 1.000 tự hiểu là đơn vị nghìn**: gõ `100` = 100.000 đ, gõ `1000` hoặc `1.000` vẫn giữ nguyên là 1.000 đ (vì đã ≥ 1.000 nên không nhân thêm). Áp dụng ở `_parse_amount` trong `bot.py`, dùng cho cả `/cong` và `/tru`.
- **Dấu âm là trách nhiệm của `bot.py`**: user luôn gõ số dương ở `/cong` và `/tru`; `bot.py` tự nhân `-1` trước khi gọi `storage.add_transaction` khi xử lý `/tru`. `storage.py` không tự đoán dấu từ tên lệnh.
- **sqlite3 chuẩn (blocking) là đủ dùng** ở quy mô 1 user — KHÔNG thêm `aiosqlite` hay DB layer async trừ khi được yêu cầu rõ ràng, dù `python-telegram-bot` v21 chạy async.
- **`created_at` lưu theo giờ Việt Nam** (`datetime.now()` local, không dùng `CURRENT_TIMESTAMP` mặc định UTC của SQLite), để lọc `/ls` theo ngày/tháng/năm không bị lệch múi giờ.
- **Không để lỗi input làm crash bot**: thiếu số tiền, số tiền không parse được, ngày sai định dạng ở `/ls` → bắt lỗi (`try/except`) và trả lời tiếng Việt thân thiện, không để exception rơi ra ngoài handler.
- **Lệnh không tồn tại** (vd gõ nhầm `/clear`, `/abc`) → bắt bằng `MessageHandler(filters.COMMAND, ...)` đăng ký sau cùng, trả lời "Lệnh không hợp lệ" kèm danh sách lệnh (`HELP_TEXT`) thay vì im lặng.
- Không có test tự động — khi sửa `storage.py`/`bot.py`, verify thủ công bằng cách chạy bot thật và gửi lệnh trong Telegram.
- Không commit `.env` hoặc `data/money.db` (đã có trong `.gitignore`).

## 7. Hướng mở rộng (chưa làm, ghi lại để giữ ngữ cảnh)

- Phân loại giao dịch theo danh mục (ăn uống, đi lại...).
- Lệnh sửa/xoá giao dịch theo id.
- Báo cáo tổng theo ngày/tháng (`/thang`).
- Nếu sau này cần nhiều người dùng/nhiều nhóm: thêm cột `chat_id` vào bảng `transactions` và lọc theo `update.effective_chat.id` trong mỗi handler.
