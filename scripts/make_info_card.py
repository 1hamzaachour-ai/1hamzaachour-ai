"""Write info-card.svg: a neofetch-style panel that prints itself line by line.

Edit INFO below when your role, stack or highlights change, then re-run:

    python scripts/make_info_card.py          # STATIC=1 for a frozen preview
"""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from terminal_theme import BLUE, BODY, GREEN, MONO, MUTED, STATIC, TEXT, WHOAMI_H, svg, window

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "info-card.svg"

USER, HOST = "hamza", "github"
INFO = [
    ("Role", "Data Analyst & AI Developer"),
    ("Now", "BI student @ FSEG Tunis · 2nd year"),
    ("Prev", "Intern @ Arab Tunisian Bank · data & APIs"),
    ("Stack", ["Python · SQL · pandas · Power BI",
               "Streamlit · Plotly · PostgreSQL · FastAPI"]),
    ("AI", "LLMs & RAG · Gemini · Groq (LLaMA 3.1)"),
    ("Highlights", ["▸ Choufli Data: retail BI + Derja AI agent",
                    "▸ T GAP: ATM locator shipped for ATB",
                    "▸ Car Market Analyzer: ETL → star schema"]),
    ("Speaks", "Arabic · French · English"),
    ("Based in", "Tunisia"),
    ("Open to", "data, AI & BI opportunities"),
    ("Contact", "1hamza.achour@gmail.com"),
]
# neofetch's colour strip: black red green yellow blue magenta cyan white
BLOCKS = ["#484f58", "#ff7b72", "#3fb950", "#d29922", "#58a6ff", "#bc8cff", "#39c5cf", "#b1bac4"]

W, H = 482, WHOAMI_H
X, VAL_X = 22, 118
TOP, LH = 58, 20
CW = 7.8                      # advance of a 13px monospace glyph
START, STAGGER = 0.35, 0.11   # seconds


def value_spans(value: str) -> str:
    """Dim the · separators; in highlight lines, accent the bullet and bold the project name."""
    if value.startswith("▸ "):
        name, _, rest = value[2:].partition(":")
        return (f'<tspan fill="{GREEN}">▸ </tspan><tspan fill="{TEXT}" font-weight="700">{escape(name)}</tspan>'
                f'<tspan fill="{BODY}">:{escape(rest)}</tspan>')
    dot = f'<tspan fill="{MUTED}"> · </tspan>'
    return dot.join(f'<tspan fill="{BODY}">{escape(part)}</tspan>' for part in value.split(" · "))


def line(i: int, inner: str) -> str:
    delay = "" if STATIC else f' style="animation-delay:{START + i * STAGGER:.2f}s"'
    return f'\n  <g class="ln"{delay}>{inner}</g>'


def render() -> str:
    rows = [
        f'<text x="{X}" y="{TOP}" font-size="14" font-weight="700"><tspan fill="{GREEN}">{USER}</tspan>'
        f'<tspan fill="{TEXT}">@</tspan><tspan fill="{GREEN}">{HOST}</tspan></text>',
        f'<text x="{X}" y="{TOP + LH}" font-size="13" fill="{MUTED}">{"-" * len(USER + "@" + HOST)}</text>',
    ]
    for key, value in INFO:
        for j, text in enumerate([value] if isinstance(value, str) else value):
            y = TOP + LH * len(rows)
            label = f'<text x="{X}" y="{y}" font-size="13" font-weight="700" fill="{BLUE}">{escape(key)}</text>' if j == 0 else ""
            rows.append(f'{label}<text x="{VAL_X}" y="{y}" font-size="13">{value_spans(text)}</text>')

    y = TOP + LH * (len(rows) - 1)
    strip = "".join(f'<rect x="{X + i * 26}" y="{y + 14}" width="26" height="16" fill="{c}"/>' for i, c in enumerate(BLOCKS))
    # textLength pins the prompt's width in any monospace font, so the cursor lands right after it.
    ps1 = f"{USER}@{HOST}:~$"
    prompt = (f'<text x="{X}" y="{y + 56}" font-size="13" textLength="{len(ps1) * CW:.1f}" lengthAdjust="spacing">'
              f'<tspan fill="{GREEN}">{USER}@{HOST}</tspan><tspan fill="{BODY}">:</tspan>'
              f'<tspan fill="{BLUE}">~</tspan><tspan fill="{BODY}">$</tspan></text>'
              f'<rect class="cur" x="{X + (len(ps1) + 1) * CW:.1f}" y="{y + 44}" width="8" height="15" fill="{BODY}"/>')
    rows += [strip, prompt]

    label = "neofetch-style card: " + "; ".join(
        f"{k}: {v if isinstance(v, str) else ', '.join(s.lstrip('▸ ') for s in v)}" for k, v in INFO)
    body = window(W, H, "neofetch") + f'\n  <g font-family="{MONO}">' + "".join(line(i, r) for i, r in enumerate(rows)) + "\n  </g>"
    return svg(W, H, label, styles(), body)


def styles() -> str:
    if STATIC:
        return ""
    return (".ln{opacity:0;animation:ln .4s ease-out forwards}"
            "@keyframes ln{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}"
            ".cur{animation:blink 1.1s steps(1,end) infinite}@keyframes blink{50%{opacity:0}}"
            "@media (prefers-reduced-motion:reduce){.ln{animation:none;opacity:1}.cur{animation:none}}")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
