"""Parse bộ lọc ngày/tháng/năm dùng chung giữa bot Telegram và web dashboard."""

import re

DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
MONTH_RE = re.compile(r"^(\d{1,2})/(\d{4})$")
YEAR_RE = re.compile(r"^(\d{4})$")


def parse_date_filter(arg: str) -> tuple[int | None, int | None, int | None] | None:
    """Parse ngày (dd/mm/yyyy), tháng (mm/yyyy) hoặc năm (yyyy). Trả về None nếu sai định dạng."""
    if not arg:
        return None, None, None
    if m := DATE_RE.match(arg):
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    if m := MONTH_RE.match(arg):
        return None, int(m.group(1)), int(m.group(2))
    if m := YEAR_RE.match(arg):
        return None, None, int(m.group(1))
    return None
