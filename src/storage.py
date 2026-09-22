"""Lưu trữ giao dịch thu chi bằng SQLite (data/money.db)."""

import calendar
import os
import sqlite3
from datetime import datetime
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "money.db"
DB_PATH = Path(os.environ["MONEY_DB_PATH"]) if os.environ.get("MONEY_DB_PATH") else _DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Tạo bảng transactions nếu chưa có."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def add_transaction(amount: int, note: str = "") -> None:
    """Thêm giao dịch. amount âm = trừ tiền, dương = cộng tiền."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO transactions (amount, note, created_at) VALUES (?, ?, ?)",
            (amount, note, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def get_balance() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions").fetchone()
        return row[0]


def _date_conditions(day: int | None, month: int | None, year: int | None) -> tuple[list[str], list[str]]:
    conditions = []
    params: list[str] = []
    if year is not None:
        conditions.append("strftime('%Y', created_at) = ?")
        params.append(f"{year:04d}")
    if month is not None:
        conditions.append("strftime('%m', created_at) = ?")
        params.append(f"{month:02d}")
    if day is not None:
        conditions.append("strftime('%d', created_at) = ?")
        params.append(f"{day:02d}")
    return conditions, params


def get_history(day: int | None = None, month: int | None = None, year: int | None = None, limit: int = 10):
    """Lấy lịch sử giao dịch, mới nhất trước.

    - Không truyền gì: `limit` giao dịch gần nhất.
    - Truyền year (+ month, + day): lọc theo năm / tháng-năm / ngày-tháng-năm.
    """
    conditions, params = _date_conditions(day, month, year)
    query = "SELECT id, amount, note, created_at FROM transactions"

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC, id DESC"

    if year is None:
        query += " LIMIT ?"
        params.append(limit)

    with _connect() as conn:
        return conn.execute(query, params).fetchall()


def get_stats(day: int | None = None, month: int | None = None, year: int | None = None) -> tuple[int, int]:
    """Tổng tiền cộng và tổng tiền trừ trong khoảng lọc (không lọc = toàn bộ lịch sử).

    Trả về (tong_cong, tong_tru) — tong_tru là số dương (đã lấy trị tuyệt đối).
    """
    conditions, params = _date_conditions(day, month, year)
    query = (
        "SELECT COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0), "
        "COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0) "
        "FROM transactions"
    )
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    with _connect() as conn:
        row = conn.execute(query, params).fetchone()
        return row[0], row[1]


def _period_days(day: int | None, month: int | None, year: int | None) -> int:
    """Số ngày trong khoảng lọc, dùng để tính trung bình/ngày.

    Tháng/năm hiện tại (chưa kết thúc) tính theo số ngày đã trôi qua, không tính cả tháng/năm
    trọn vẹn, để không làm loãng số trung bình.
    """
    today = datetime.now().date()

    if day is not None:
        return 1

    if month is not None and year is not None:
        if year == today.year and month == today.month:
            return today.day
        return calendar.monthrange(year, month)[1]

    if year is not None:
        if year == today.year:
            return today.timetuple().tm_yday
        return 366 if calendar.isleap(year) else 365

    with _connect() as conn:
        row = conn.execute("SELECT MIN(created_at) FROM transactions").fetchone()
    if row[0] is None:
        return 1
    first_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").date()
    return max((today - first_date).days + 1, 1)


def get_average(day: int | None = None, month: int | None = None, year: int | None = None) -> tuple[int, int, int]:
    """Trung bình tiền cộng/trừ mỗi ngày trong khoảng lọc.

    Trả về (tb_cong, tb_tru, so_ngay).
    """
    total_in, total_out = get_stats(day=day, month=month, year=year)
    num_days = _period_days(day, month, year)
    return total_in // num_days, total_out // num_days, num_days


def get_top_expenses(day: int | None = None, month: int | None = None, year: int | None = None, limit: int = 5):
    """Top khoản chi (amount âm) lớn nhất trong khoảng lọc, lớn nhất trước."""
    conditions, params = _date_conditions(day, month, year)
    query = "SELECT id, amount, note, created_at FROM transactions WHERE amount < 0"
    if conditions:
        query += " AND " + " AND ".join(conditions)
    query += " ORDER BY amount ASC LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        return conn.execute(query, params).fetchall()
