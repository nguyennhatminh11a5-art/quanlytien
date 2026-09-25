"""Web dashboard xem thống kê thu chi (chỉ xem, không sửa/xoá). Entry point: python src/web.py

Chạy song song với bot.py, đọc chung SQLite DB (qua MONEY_DB_PATH). Chỉ nên mở trên
localhost - không có xác thực đăng nhập, không thiết kế để expose ra mạng ngoài.
"""

from datetime import datetime

from flask import Flask, render_template, request

import storage
from dateparse import parse_date_filter

app = Flask(__name__)


def _format_money(value: int) -> str:
    return f"{value:,}".replace(",", ".")


app.jinja_env.filters["money"] = _format_money


@app.route("/")
def dashboard():
    today = datetime.now()
    balance = storage.get_balance()
    total_in, total_out = storage.get_stats(month=today.month, year=today.year)
    avg_in, avg_out, num_days = storage.get_average(month=today.month, year=today.year)
    top_expenses = storage.get_top_expenses(month=today.month, year=today.year, limit=5)
    return render_template(
        "dashboard.html",
        active="dashboard",
        balance=balance,
        total_in=total_in,
        total_out=total_out,
        avg_in=avg_in,
        avg_out=avg_out,
        num_days=num_days,
        top_expenses=top_expenses,
        thang=today.month,
        nam=today.year,
    )


@app.route("/history")
def history():
    filter_arg = request.args.get("loc", "").strip()
    error = None
    day = month = year = None

    if filter_arg:
        parsed = parse_date_filter(filter_arg)
        if parsed is None:
            error = "Định dạng không hợp lệ. Dùng: ngày (22/09/2026), tháng (09/2026) hoặc năm (2026)."
        else:
            day, month, year = parsed

    rows = [] if error else storage.get_history(day=day, month=month, year=year, limit=20)
    return render_template("history.html", active="history", rows=rows, filter_arg=filter_arg, error=error)


if __name__ == "__main__":
    storage.init_db()
    app.run(host="0.0.0.0", port=5000)
