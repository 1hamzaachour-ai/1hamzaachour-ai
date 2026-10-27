"""Turn a prepped grayscale image into a self-typing ASCII-art SVG.

Each cell's darkness picks a glyph from RAMP, so white prints as blank space and
the subject as one-colour text. Every row is wiped in left to right by a clip,
with a block cursor riding the edge (SMIL, which GitHub plays inside an <img>),
staggered top to bottom. It prints once and freezes.

    python scripts/prep_photo.py my-photo.jpg     # -> source-prepped.png
    python scripts/make_ascii_svg.py              # -> assets/ascii-portrait.svg
"""
from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageOps

from terminal_theme import BAR_H, BG, BODY, GREEN, MONO, STATIC, WHOAMI_H, svg, window

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source-prepped.png"
OUT = ROOT / "assets" / "ascii-portrait.svg"

RAMP = " .`:-=+*cs#%@"   # bright (sparse) -> dark (dense); the leading space clears white to nothing
W, H = 360, WHOAMI_H
PAD = 14
AREA = (PAD, BAR_H + PAD, W - 2 * PAD, H - BAR_H - 2 * PAD)   # x, y, width, height the glyphs fill
GLYPH = 0.6               # monospace advance / font size
LINE = 1.12               # row pitch / font size
START, STAGGER = 0.3, 0.055


def cell_size(cols: int) -> tuple[float, float, int]:
    """Cell width and height (cells are taller than wide) and how many rows fit."""
    cw = AREA[2] / cols
    ch = cw / GLYPH * LINE
    return cw, ch, int(AREA[3] // ch)


def to_grid(img: Image.Image, cols: int, gamma: float = 1.0) -> tuple[list[str], tuple[int, int, int, int]]:
    """Downsample to rows of glyphs, letterboxed into the area.

    Also returns where the image landed: first column, first row, columns, rows.
    """
    cw, ch, rows = cell_size(cols)
    gray = ImageOps.grayscale(img)
    scale = min(AREA[2] / gray.width, rows * ch / gray.height)
    gc = min(cols, max(1, round(gray.width * scale / cw)))
    gr = min(rows, max(1, round(gray.height * scale / ch)))
    small = gray.resize((gc, gr), Image.Resampling.BOX)
    c0, r0 = (cols - gc) // 2, (rows - gr) // 2

    top = len(RAMP) - 1
    grid = [[" "] * cols for _ in range(rows)]
    for r in range(gr):
        for c in range(gc):
            ink = (1 - small.getpixel((c, r)) / 255) ** gamma
            grid[r0 + r][c0 + c] = RAMP[min(top, int(ink * top + 0.5))]
    return ["".join(row) for row in grid], (c0, r0, gc, gr)


def render(lines: list[str], title: str, *, fill: str = BODY, note: str = "",
           pin: tuple[float, float, str] | None = None) -> str:
    """Rows of glyphs -> SVG. pin = (column, row, label) drops a labelled dot there, e.g. a city."""
    cw, ch, _ = cell_size(len(lines[0]))
    ax, ay, aw, _ = AREA
    defs, rows, cursors = [], [], []
    done = START
    for r, line in enumerate(lines):
        body = line.strip()
        if not body:
            continue
        x0 = ax + (len(line) - len(line.lstrip())) * cw
        y0 = ay + r * ch
        tl = len(body) * cw
        # Non-breaking spaces survive SVG whitespace collapsing; textLength locks the glyph pitch.
        text = escape(body).replace(" ", " ")
        attrs = f'x="{x0:.2f}" y="{y0 + ch * 0.78:.2f}" textLength="{tl:.2f}" lengthAdjust="spacing"'
        if STATIC:
            rows.append(f"<text {attrs}>{text}</text>")
            continue
        begin, dur = START + r * STAGGER, 0.18 + 0.32 * tl / aw
        done = max(done, begin + dur)
        defs.append(f'<clipPath id="w{r}"><rect x="{x0:.2f}" y="{y0:.2f}" width="0" height="{ch + 0.5:.2f}">'
                    f'<animate attributeName="width" to="{tl:.2f}" begin="{begin:.3f}s" dur="{dur:.3f}s" fill="freeze"/>'
                    f"</rect></clipPath>")
        rows.append(f'<text {attrs} clip-path="url(#w{r})">{text}</text>')
        cursors.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{cw:.2f}" height="{ch:.2f}" opacity="0">'
                       f'<animate attributeName="x" to="{x0 + tl:.2f}" begin="{begin:.3f}s" dur="{dur:.3f}s" fill="freeze"/>'
                       f'<set attributeName="opacity" to="1" begin="{begin:.3f}s"/>'
                       f'<set attributeName="opacity" to="0" begin="{begin + dur:.3f}s"/></rect>')

    body = (window(W, H, title, note)
            + (f"\n  <defs>{''.join(defs)}</defs>" if defs else "")
            + f'\n  <g font-family="{MONO}" font-size="{cw / GLYPH:.2f}" fill="{fill}">\n    '
            + "\n    ".join(rows) + "\n  </g>"
            + (f'\n  <g fill="{GREEN}">' + "".join(cursors) + "</g>" if cursors else "")
            + (marker(ax + pin[0] * cw, ay + pin[1] * ch, pin[2], done) if pin else ""))
    label = f"ASCII art: {title}" + (f", {pin[2]} marked" if pin else "")
    return svg(W, H, label, "", body)


def marker(x: float, y: float, label: str, at: float) -> str:
    """A labelled dot that drops in once the art has printed, then pings a few times."""
    if STATIC:
        head = "<g>"
    else:
        head = (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{at:.2f}s"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="none" stroke="{GREEN}" stroke-width="1.5" opacity="0">'
                f'<animate attributeName="r" from="3" to="15" begin="{at:.2f}s" dur="1.4s" repeatCount="3"/>'
                f'<animate attributeName="opacity" from="0.9" to="0" begin="{at:.2f}s" dur="1.4s" repeatCount="3"/></circle>')
    return (f"\n  {head}"
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{GREEN}" stroke="{BG}" stroke-width="1.5"/>'
            f'<text x="{x + 8:.1f}" y="{y - 6:.1f}" font-family="{MONO}" font-size="11" font-weight="700" '
            f'fill="{GREEN}" stroke="{BG}" stroke-width="3" paint-order="stroke">{escape(label)}</text></g>')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", nargs="?", type=Path, default=SOURCE, help="prepped grayscale image (default: source-prepped.png)")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--title", default="~/hamza.ascii", help="text in the window title bar")
    parser.add_argument("--cols", type=int, default=96, help="characters per row")
    parser.add_argument("--gamma", type=float, default=1.0, help=">1 lightens mid-tones, <1 darkens them")
    args = parser.parse_args()

    lines, _ = to_grid(Image.open(args.image), args.cols, args.gamma)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(lines, args.title), encoding="utf-8")
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
