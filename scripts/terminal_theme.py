"""Shared look for the profile SVGs: a dark terminal window with a title bar."""
from __future__ import annotations

import os
from xml.sax.saxutils import escape

BG, BORDER, BAR = "#0d1117", "#30363d", "#161b22"
TEXT, BODY, MUTED = "#e6edf3", "#c9d1d9", "#8b949e"
GREEN, BLUE = "#3fb950", "#58a6ff"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
BAR_H = 30
WHOAMI_H = 420   # portrait and info card share a height so they line up side by side

# STATIC=1 writes a frozen final frame (no animation) for local previews.
STATIC = os.environ.get("STATIC") == "1"


def window(w: float, h: float, title: str, right: str = "") -> str:
    """Rounded window, title bar with traffic lights, centred title, optional right-hand note."""
    note = (f'<text x="{w - 16}" y="19.5" text-anchor="end" font-family="{MONO}" font-size="11" '
            f'fill="{MUTED}">{escape(right)}</text>') if right else ""
    return f"""
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <path d="M0.5 {BAR_H}V10.5a10 10 0 0 1 10-10H{w - 10.5}a10 10 0 0 1 10 10V{BAR_H}Z" fill="{BAR}"/>
  <line x1="0.5" y1="{BAR_H}" x2="{w - 0.5}" y2="{BAR_H}" stroke="{BORDER}"/>
  <circle cx="18" cy="15" r="5.5" fill="#ff5f57"/><circle cx="36" cy="15" r="5.5" fill="#febc2e"/><circle cx="54" cy="15" r="5.5" fill="#28c840"/>
  <text x="{w / 2}" y="19.5" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{MUTED}">{escape(title)}</text>{note}"""


def svg(w: float, h: float, label: str, style: str, body: str) -> str:
    """Wrap a body in an accessible <svg> root."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label, {'"': '&quot;'})}">
  <title>{escape(label)}</title>
  <style>{style}</style>{body}
</svg>
"""
