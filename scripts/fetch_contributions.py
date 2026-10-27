"""Scrape the public GitHub contribution calendar into data/contributions.json.

GitHub serves the calendar shown on every profile page as a public HTML fragment
at https://github.com/users/<username>/contributions, so no API token is needed.

    python scripts/fetch_contributions.py [--user USERNAME]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"
DEFAULT_USER = "1hamzaachour-ai"
URL = "https://github.com/users/{user}/contributions"

COUNT_RE = re.compile(r"^\s*([\d,]+)\s+contributions?\b", re.IGNORECASE)
TOTAL_RE = re.compile(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", re.IGNORECASE)


def fetch_html(user: str) -> str:
    resp = requests.get(
        URL.format(user=user),
        headers={"User-Agent": f"profile-art/1.0 (+https://github.com/{user})", "Accept": "text/html"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def parse_calendar(html: str) -> tuple[list[dict], int | None]:
    """Return the day cells (sorted by date) and GitHub's own yearly total."""
    soup = BeautifulSoup(html, "html.parser")
    # Each day cell has an id; its count lives in a <tool-tip for="that id">.
    tips = {tip.get("for"): tip.get_text(" ", strip=True) for tip in soup.find_all("tool-tip")}

    days = []
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        match = COUNT_RE.match(tips.get(cell.get("id"), ""))  # "No contributions on ..." -> 0
        days.append({
            "date": cell["data-date"],
            "count": int(match.group(1).replace(",", "")) if match else 0,
            "level": int(cell.get("data-level", 0)),
        })
    days.sort(key=lambda d: d["date"])

    total = TOTAL_RE.search(" ".join(soup.get_text(" ").split()))
    return days, int(total.group(1).replace(",", "")) if total else None


def streaks(days: list[dict]) -> tuple[int, int]:
    """(current, longest) runs of consecutive active days.

    A quiet *today* doesn't break the current streak, since the day isn't over yet.
    """
    longest = run = 0
    for day in days:
        run = run + 1 if day["count"] else 0
        longest = max(longest, run)

    i = len(days) - 1
    if i >= 0 and days[i]["count"] == 0:
        i -= 1
    current = 0
    while i >= 0 and days[i]["count"]:
        current += 1
        i -= 1
    return current, longest


def summarize(user: str, days: list[dict], header_total: int | None) -> dict:
    total = sum(d["count"] for d in days)
    current, longest = streaks(days)
    best = max(reversed(days), key=lambda d: d["count"])  # ties -> most recent day
    monthly: dict[str, int] = {}
    for day in days:
        monthly[day["date"][:7]] = monthly.get(day["date"][:7], 0) + day["count"]

    return {
        "user": user,
        "fetched_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "stats": {
            "total": header_total if header_total is not None else total,
            "active_days": sum(1 for d in days if d["count"]),
            "current_streak": current,
            "longest_streak": longest,
            "best_day": {"date": best["date"], "count": best["count"]},
        },
        "monthly": monthly,
        "days": days,
    }


def dump(payload: dict) -> str:
    """Pretty JSON, but one day per line so the daily commit diffs stay readable."""
    days = payload["days"]
    text = json.dumps({**payload, "days": "__DAYS__"}, indent=2)
    rows = ",\n".join("    " + json.dumps(d) for d in days)
    return text.replace('"__DAYS__"', "[\n" + rows + "\n  ]") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", default=DEFAULT_USER)
    args = parser.parse_args()

    days, header_total = parse_calendar(fetch_html(args.user))

    # Refuse to overwrite good data with a half-parsed page if GitHub changes its markup.
    if len(days) < 350:
        print(f"error: parsed only {len(days)} days -- calendar markup may have changed", file=sys.stderr)
        return 1
    summed = sum(d["count"] for d in days)
    if header_total is not None and header_total != summed:
        print(f"warning: header says {header_total} contributions, cells sum to {summed}", file=sys.stderr)

    payload = summarize(args.user, days, header_total)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(dump(payload), encoding="utf-8")

    s = payload["stats"]
    print(f"{args.user}: {s['total']} contributions, {s['active_days']} active days, "
          f"streak {s['current_streak']} (longest {s['longest_streak']}), "
          f"{payload['range']['start']} -> {payload['range']['end']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
