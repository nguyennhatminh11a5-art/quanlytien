"""Bot Telegram quản lý thu chi cá nhân. Entry point: python src/bot.py"""

import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

import storage
from dateparse import parse_date_filter

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])


def _is_allowed(update: Update) -> bool:
    return update.effective_chat is not None and update.effective_chat.id == ALLOWED_CHAT_ID


def _parse_amount(raw: str) -> int | None:
    """Bỏ mọi dấu chấm/phẩy, chỉ chấp nhận số nguyên dương.

    Số dưới 1.000 được hiểu theo đơn vị nghìn (vd "100" -> 100.000 đ),
    vì trong giao tiếp thường ngày không ai nói số tiền dưới 1.000 đ.
    """
    cleaned = raw.replace(".", "").replace(",", "")
    if not cleaned.isdigit():
        return None
    amount = int(cleaned)
    if 0 < amount < 1000:
        amount *= 1000
    return amount


HELP_TEXT = (
    "Bot quản lý thu chi cá nhân.\n\n"
    "/cong <số tiền> [ghi chú] - Cộng tiền, vd: /cong 50000 an sang\n"
    "/tru <số tiền> [ghi chú] - Trừ tiền, vd: /tru 20000 gui xe\n"
    "/so - Xem số dư hiện tại\n"
    "/ls [ngày|tháng/năm|năm] - Xem lịch sử giao dịch\n"
    "/thongke [ngày|tháng/năm|năm] - Tổng cộng/trừ theo khoảng thời gian\n"
    "/trungbinh [ngày|tháng/năm|năm] - Trung bình cộng/trừ mỗi ngày\n"
    "/top [n] [ngày|tháng/năm|năm] - n khoản chi lớn nhất, vd: /top 5 09/2026\n"
    "/help - Xem lại danh sách lệnh này"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def cong(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Thiếu số tiền. Vd: /cong 50000 an sang")
        return
    amount = _parse_amount(context.args[0])
    if amount is None:
        await update.message.reply_text("Số tiền không hợp lệ. Vd: /cong 50000 an sang")
        return
    note = " ".join(context.args[1:])
    storage.add_transaction(amount, note)
    balance = storage.get_balance()
    await update.message.reply_text(f"Đã cộng {amount:,} đ. Số dư hiện tại: {balance:,} đ".replace(",", "."))


async def tru(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    if not context.args:
        await update.message.reply_text("Thiếu số tiền. Vd: /tru 20000 gui xe")
        return
    amount = _parse_amount(context.args[0])
    if amount is None:
        await update.message.reply_text("Số tiền không hợp lệ. Vd: /tru 20000 gui xe")
        return
    note = " ".join(context.args[1:])
    storage.add_transaction(-amount, note)
    balance = storage.get_balance()
    await update.message.reply_text(f"Đã trừ {amount:,} đ. Số dư hiện tại: {balance:,} đ".replace(",", "."))


async def so(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    balance = storage.get_balance()
    await update.message.reply_text(f"Số dư hiện tại: {balance:,} đ".replace(",", "."))


async def ls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return

    day = month = year = None
    if context.args:
        parsed = parse_date_filter(context.args[0])
        if parsed is None:
            await update.message.reply_text(
                "Định dạng không hợp lệ. Dùng: ngày (22/09/2026), tháng (09/2026) hoặc năm (2026)."
            )
            return
        day, month, year = parsed

    rows = storage.get_history(day=day, month=month, year=year)
    if not rows:
        await update.message.reply_text("Không có giao dịch nào.")
        return

    lines = []
    for _id, amount, note, created_at in rows:
        sign = "+" if amount >= 0 else ""
        note_part = f" - {note}" if note else ""
        lines.append(f"{created_at}: {sign}{amount:,} đ{note_part}".replace(",", "."))
    await update.message.reply_text("\n".join(lines))


async def thongke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return

    day = month = year = None
    if context.args:
        parsed = parse_date_filter(context.args[0])
        if parsed is None:
            await update.message.reply_text(
                "Định dạng không hợp lệ. Dùng: ngày (22/09/2026), tháng (09/2026) hoặc năm (2026)."
            )
            return
        day, month, year = parsed

    total_in, total_out = storage.get_stats(day=day, month=month, year=year)
    label = "toàn bộ" if not context.args else context.args[0]
    await update.message.reply_text(
        f"Thống kê ({label}):\n"
        f"Tổng cộng: +{total_in:,} đ\n"
        f"Tổng trừ: -{total_out:,} đ\n"
        f"Chênh lệch: {total_in - total_out:,} đ".replace(",", ".")
    )


async def trungbinh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return

    day = month = year = None
    if context.args:
        parsed = parse_date_filter(context.args[0])
        if parsed is None:
            await update.message.reply_text(
                "Định dạng không hợp lệ. Dùng: ngày (22/09/2026), tháng (09/2026) hoặc năm (2026)."
            )
            return
        day, month, year = parsed

    avg_in, avg_out, num_days = storage.get_average(day=day, month=month, year=year)
    label = "toàn bộ" if not context.args else context.args[0]
    await update.message.reply_text(
        f"Trung bình/ngày ({label}, {num_days} ngày):\n"
        f"Cộng: +{avg_in:,} đ\n"
        f"Trừ: -{avg_out:,} đ".replace(",", ".")
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return

    args = context.args
    n = 5
    date_arg = None
    if args:
        if args[0].isdigit() and int(args[0]) < 100:
            n = int(args[0])
            if len(args) > 1:
                date_arg = args[1]
        else:
            date_arg = args[0]

    day = month = year = None
    if date_arg is not None:
        parsed = parse_date_filter(date_arg)
        if parsed is None:
            await update.message.reply_text(
                "Định dạng không hợp lệ. Dùng: ngày (22/09/2026), tháng (09/2026) hoặc năm (2026)."
            )
            return
        day, month, year = parsed

    rows = storage.get_top_expenses(day=day, month=month, year=year, limit=n)
    if not rows:
        await update.message.reply_text("Không có giao dịch chi tiêu nào.")
        return

    lines = [f"Top {len(rows)} khoản chi lớn nhất:"]
    for _id, amount, note, created_at in rows:
        note_part = f" - {note}" if note else ""
        lines.append(f"{created_at}: {amount:,} đ{note_part}".replace(",", "."))
    await update.message.reply_text("\n".join(lines))


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_allowed(update):
        return
    await update.message.reply_text("Lệnh không hợp lệ.\n\n" + HELP_TEXT)


def main() -> None:
    storage.init_db()
    request = HTTPXRequest(connect_timeout=30, read_timeout=30, write_timeout=30, pool_timeout=30)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cong", cong))
    app.add_handler(CommandHandler("tru", tru))
    app.add_handler(CommandHandler("so", so))
    app.add_handler(CommandHandler("ls", ls))
    app.add_handler(CommandHandler("thongke", thongke))
    app.add_handler(CommandHandler("trungbinh", trungbinh))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_command))
    app.run_polling()


if __name__ == "__main__":
    main()
