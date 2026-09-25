"""Vẽ biểu đồ SVG server-side cho web dashboard (không phụ thuộc JS).

Màu lấy từ palette đã validate (xem dataviz skill): cặp diverging xanh/đỏ cho
phân cực thu (dương) / chi (âm), neutral gray cho baseline.
"""

BLUE = "#3987e5"
RED = "#e66767"
BASELINE_GRAY = "#383835"
GRID_GRAY = "#2c2c2a"
MUTED = "#898781"

_CHART_W = 640
_CHART_H = 160
_PAD_X = 8
_PAD_TOP = 16
_PAD_BOTTOM = 20
_GAP = 2
_RADIUS = 3


def _rounded_bar_path(x: float, baseline_y: float, width: float, height: float, up: bool) -> str:
    """Path cho 1 cột, bo góc 2 đầu xa baseline, đầu chạm baseline vuông góc."""
    if height <= 0.5:
        return ""
    r = min(_RADIUS, width / 2, height)
    if up:
        top = baseline_y - height
        return (
            f"M{x:.1f},{baseline_y:.1f} "
            f"L{x:.1f},{top + r:.1f} "
            f"Q{x:.1f},{top:.1f} {x + r:.1f},{top:.1f} "
            f"L{x + width - r:.1f},{top:.1f} "
            f"Q{x + width:.1f},{top:.1f} {x + width:.1f},{top + r:.1f} "
            f"L{x + width:.1f},{baseline_y:.1f} Z"
        )
    bottom = baseline_y + height
    return (
        f"M{x:.1f},{baseline_y:.1f} "
        f"L{x:.1f},{bottom - r:.1f} "
        f"Q{x:.1f},{bottom:.1f} {x + r:.1f},{bottom:.1f} "
        f"L{x + width - r:.1f},{bottom:.1f} "
        f"Q{x + width:.1f},{bottom:.1f} {x + width:.1f},{bottom - r:.1f} "
        f"L{x + width:.1f},{baseline_y:.1f} Z"
    )


def daily_net_svg(daily_net: list[tuple[int, int]]) -> str:
    """SVG cột chênh lệch thu-chi mỗi ngày. daily_net: [(ngay, net_amount), ...]."""
    if not daily_net:
        return ""

    plot_h = _CHART_H - _PAD_TOP - _PAD_BOTTOM
    baseline_y = _PAD_TOP + plot_h / 2
    max_abs = max(1, max(abs(net) for _, net in daily_net))

    n = len(daily_net)
    plot_w = _CHART_W - 2 * _PAD_X
    bar_w = max(1.0, (plot_w - _GAP * (n - 1)) / n)

    label_every = max(1, n // 8)
    bars = []
    labels = []
    for i, (day, net) in enumerate(daily_net):
        x = _PAD_X + i * (bar_w + _GAP)
        height = (abs(net) / max_abs) * (plot_h / 2 - 4)
        color = BLUE if net >= 0 else RED
        path = _rounded_bar_path(x, baseline_y, bar_w, height, up=net >= 0)
        title = f"Ngày {day:02d}: {'+' if net >= 0 else ''}{net:,} đ".replace(",", ".")
        if path:
            bars.append(f'<path d="{path}" fill="{color}"><title>{title}</title></path>')
        if day % label_every == 0 or day == 1:
            labels.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{_CHART_H - 4}" '
                f'font-size="9" fill="{MUTED}" text-anchor="middle">{day}</text>'
            )

    svg = (
        f'<svg viewBox="0 0 {_CHART_W} {_CHART_H}" width="100%" height="{_CHART_H}" '
        f'role="img" aria-label="Biểu đồ chênh lệch thu chi theo ngày">'
        f'<line x1="{_PAD_X}" y1="{baseline_y:.1f}" x2="{_CHART_W - _PAD_X}" y2="{baseline_y:.1f}" '
        f'stroke="{BASELINE_GRAY}" stroke-width="1" />'
        + "".join(bars)
        + "".join(labels)
        + "</svg>"
    )
    return svg
