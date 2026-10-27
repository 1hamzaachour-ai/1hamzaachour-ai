"""Render data/contributions.json as an animated contribution heatmap SVG.

The boxes slide in once along a diagonal (CSS keyframes inside the SVG, which
GitHub plays when the README shows it as an <img>), then everything freezes.
Set STATIC=1 to write a frame without animation, handy for local previews.

    python scripts/render_heatmap_svg.py
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from xml.sax.saxutils import escape

from terminal_theme import MONO, MUTED, STATIC, TEXT, svg, window

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "assets" / "contrib-heatmap.svg"

# GitHub-ish greens, none -> brightest; level 5 is a neon top end for standout days.
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

W = 846               # GitHub's profile README column, so it shows at 1:1
PAD = 22
LABEL_W = 30          # weekday labels
GAP = 3
GRID_TOP = 98
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def nice_date(iso: str, year: bool = True) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.day}" + (f", {d.year}" if year else "")


def levels(days: list[dict]) -> list[int]:
    """GitHub's own 0-4 levels, plus 5 for days at least double the smallest level-4 day."""
    top = [d["count"] for d in days if d["level"] == 4 and d["count"]]
    neon = 2 * min(top) if top else None
    return [5 if neon and d["level"] == 4 and d["count"] >= neon else d["level"] for d in days]


def render(data: dict) -> str:
    days = data["days"]
    stats = data["stats"]
    start = dt.date.fromisoformat(days[0]["date"])
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)       # back to Sunday
    ncols = (dt.date.fromisoformat(days[-1]["date"]) - start).days // 7 + 1

    gx = PAD + LABEL_W
    step = (W - gx - PAD + GAP) / ncols
    cell = step - GAP
    grid_bottom = GRID_TOP + 6 * step + cell
    h = round(grid_bottom + 52)

    parts = [window(W, h, "~/contributions.sh", f"updated {nice_date(data['fetched_at'][:10])}")]

    # Headline: total + date range.
    parts.append(
        f'<text x="{PAD}" y="62" class="t fade" font-size="15">'
        f'<tspan fill="{TEXT}" font-weight="700">{stats["total"]:,} contributions</tspan>'
        f'<tspan fill="{MUTED}"> in the last year</tspan></text>'
        f'<text x="{W - PAD}" y="62" text-anchor="end" class="t muted fade" font-size="12">'
        f'{nice_date(days[0]["date"])} → {nice_date(days[-1]["date"])}</text>'
    )

    # Month labels where a column's Sunday starts a new month; drop a cramped first one.
    marks = []
    for c in range(ncols):
        sunday = start + dt.timedelta(weeks=c)
        if c == 0 or sunday.month != (sunday - dt.timedelta(weeks=1)).month:
            marks.append((c, MONTHS[sunday.month - 1]))
    if len(marks) > 1 and marks[1][0] - marks[0][0] < 3:
        marks.pop(0)
    for c, name in marks:
        parts.append(f'<text x="{gx + c * step:.1f}" y="{GRID_TOP - 9}" class="t muted fade" font-size="11">{name}</text>')
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(f'<text x="{PAD}" y="{GRID_TOP + r * step + cell - 2.5:.1f}" class="t muted fade" font-size="10">{name}</text>')

    # The grid: one rounded box per day, revealed along the col+row diagonal.
    for day, level in zip(days, levels(days)):
        d = dt.date.fromisoformat(day["date"])
        c, r = (d - start).days // 7, (d.weekday() + 1) % 7
        parts.append(
            f'<rect x="{gx + c * step:.1f}" y="{GRID_TOP + r * step:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
            f'rx="2.5" fill="{PALETTE[level]}" class="c d{c + r}"/>'
        )

    # Footer: streak stats on the left, Less -> More legend on the right.
    best = stats["best_day"]
    facts = [plural(stats["active_days"], "active day")]
    if stats["current_streak"]:
        facts.append(f"current streak {plural(stats['current_streak'], 'day')}")
    facts.append(f"longest streak {plural(stats['longest_streak'], 'day')}")
    if best["count"]:
        facts.append(f"best day {best['count']} on {nice_date(best['date'], year=False)}")
    fy = grid_bottom + 30
    parts.append(f'<text x="{PAD}" y="{fy:.1f}" class="t muted fade2" font-size="12">{escape("  ·  ".join(facts))}</text>')

    lx = W - PAD - 34 - len(PALETTE) * 15
    legend = [f'<text x="{lx - 8}" y="{fy:.1f}" text-anchor="end" class="t muted" font-size="11">Less</text>']
    for i, color in enumerate(PALETTE):
        legend.append(f'<rect x="{lx + i * 15}" y="{fy - 10:.1f}" width="11" height="11" rx="2.5" fill="{color}"/>')
    legend.append(f'<text x="{lx + len(PALETTE) * 15 + 4}" y="{fy:.1f}" class="t muted" font-size="11">More</text>')
    parts.append(f'<g class="fade2">{"".join(legend)}</g>')

    label = (f"{data['user']}'s GitHub contributions: {stats['total']} in the last year, "
             f"{stats['active_days']} active days, longest streak {stats['longest_streak']} days.")
    return svg(W, h, label, styles(ncols), "".join(parts))


def styles(ncols: int) -> str:
    base = f".t{{font-family:{MONO}}}.muted{{fill:{MUTED}}}"
    if STATIC:
        return base
    delays = "".join(f".d{i}{{animation-delay:{0.25 + i * 0.018:.3f}s}}" for i in range(ncols + 7))
    return base + (
        ".c{opacity:0;animation:drop .45s cubic-bezier(.2,.8,.3,1) forwards}"
        "@keyframes drop{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}"
        ".fade,.fade2{opacity:0;animation:fade .6s ease-out forwards}.fade2{animation-delay:1.3s}"
        "@keyframes fade{to{opacity:1}}"
        "@media (prefers-reduced-motion:reduce){.c,.fade,.fade2{animation:none;opacity:1}}"
        + delays
    )


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
