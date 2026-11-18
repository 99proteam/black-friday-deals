#!/usr/bin/env python3
"""Build the generated parts of README.md from deals.yml.

Usage:
    python scripts/build_readme.py           # rewrite README.md
    python scripts/build_readme.py --check   # fail if README.md is out of date

Only the text between <!-- NAME:START --> and <!-- NAME:END --> markers is
generated. Everything else in README.md is hand-written and left alone.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "deals.yml"
README = ROOT / "README.md"

STATUS = {
    "live": "🟢&nbsp;Live",
    "soon": "⏳&nbsp;Soon",
    "expired": "⛔&nbsp;Expired",
}
STATUS_ORDER = {"live": 0, "soon": 1, "expired": 2}
REQUIRED = ("name", "domain", "url", "description", "offer", "status")


# ---------------------------------------------------------------- validation

def validate(data: dict) -> list[str]:
    errors: list[str] = []
    names: set[str] = set()
    for cat in data.get("categories", []):
        for key in ("id", "emoji", "title", "blurb", "deals"):
            if key not in cat:
                errors.append(f"category {cat.get('id', '?')}: missing '{key}'")
        for deal in cat.get("deals", []):
            label = f"{cat.get('id')}/{deal.get('name', '?')}"
            for key in REQUIRED:
                if not deal.get(key):
                    errors.append(f"{label}: missing '{key}'")
            if deal.get("status") not in STATUS:
                errors.append(f"{label}: status must be one of {', '.join(STATUS)}")
            if not str(deal.get("url", "")).startswith("https://"):
                errors.append(f"{label}: url must start with https://")
            if "|" in str(deal.get("description", "")) + str(deal.get("offer", "")):
                errors.append(f"{label}: '|' is not allowed (it breaks the table)")
            if deal.get("name") in names:
                errors.append(f"{label}: duplicate deal name")
            names.add(deal.get("name"))
    for pick in data.get("top_picks", []):
        if pick not in names:
            errors.append(f"top_picks: '{pick}' is not a deal name")
    return errors


# ----------------------------------------------------------------- rendering

def favicon(domain: str, size: int) -> str:
    return f"https://www.google.com/s2/favicons?domain={domain}&sz={size}"


def badge(label: str, message: str, color: str, link: str | None = None) -> str:
    def esc(s: str) -> str:
        return quote(s.replace("-", "--").replace("_", "__").replace(" ", "_"), safe="_")

    img = f"![{label}](https://img.shields.io/badge/{esc(label)}-{esc(message)}-{color}?style=for-the-badge)"
    return f"[{img}]({link})" if link else img


def all_deals(data: dict):
    for cat in data["categories"]:
        yield from cat["deals"]


def fmt_date(value) -> str:
    d = value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value))
    return f"{d:%b} {d.day}, {d.year}"


def render_stats(data: dict) -> str:
    deals = list(all_deals(data))
    live = sum(d["status"] == "live" for d in deals)
    # Plain markdown (no HTML wrapper) so GitHub renders the badge images.
    # The surrounding <div align="center"> in README.md centres them.
    badges = [
        badge("deals live", f"{live} of {len(deals)}", "22c55e", "#categories"),
        badge("black friday", fmt_date(data["black_friday"]), "111827"),
        badge("cyber monday", fmt_date(data["cyber_monday"]), "6366f1"),
        badge("last checked", fmt_date(data["last_updated"]), "0ea5e9"),
    ]
    return "\n" + " ".join(badges) + "\n"


def render_nav(data: dict) -> str:
    chips = []
    for cat in data["categories"]:
        chips.append(
            f'<a href="#{cat["id"]}">{cat["emoji"]}&nbsp;{cat["title"].replace(" ", "&nbsp;")}</a>&nbsp;<code>{len(cat["deals"])}</code>'
        )
    return '<p align="center">\n  ' + " &nbsp;·&nbsp;\n  ".join(chips) + "\n</p>"


def render_top_picks(data: dict) -> str:
    by_name = {d["name"]: d for d in all_deals(data)}
    picks = [by_name[n] for n in data.get("top_picks", [])]
    width = f"{100 // max(len(picks), 1)}%"
    cells = []
    for d in picks:
        code = f"<br><code>{d['code']}</code>" if d.get("code") else "<br><sub>No code needed</sub>"
        cells.append(
            f'    <td align="center" width="{width}">\n'
            f'      <a href="{d["url"]}"><img src="{favicon(d["domain"], 64)}" width="40" height="40" alt=""><br>'
            f'<b>{d["name"]}</b></a><br>\n'
            f'      <sub>{d["offer"]}</sub>{code}\n'
            f"    </td>"
        )
    return "<table>\n  <tr>\n" + "\n".join(cells) + "\n  </tr>\n</table>"


def render_row(d: dict) -> str:
    icon = f'<img src="{favicon(d["domain"], 32)}" width="20" height="20" alt="">'
    name = f'**[{d["name"]}]({d["url"]})**<br><sub>{d["description"]}</sub>'
    offer = d["offer"]
    if d["status"] == "soon":
        offer = f"<i>{offer}</i>"
    else:
        offer = f"**{offer}**"
    if d.get("hot"):
        offer = f"🔥 {offer}"
    if d.get("valid"):
        offer += f"<br><sub>⌛ {d['valid']}</sub>"
    if d.get("code"):
        code = f"`{d['code']}`"
    elif d["status"] == "live":
        code = "<sub>Not needed</sub>"
    else:
        code = "—"
    return f"| {icon} | {name} | {offer} | {code} | {STATUS[d['status']]} |"


def render_deals(data: dict) -> str:
    out: list[str] = []
    for cat in data["categories"]:
        deals = sorted(cat["deals"], key=lambda d: STATUS_ORDER[d["status"]])
        out.append(f'<a id="{cat["id"]}"></a>\n')
        out.append(f"## {cat['emoji']} {cat['title']}\n")
        out.append(f"> {cat['blurb']}\n")
        out.append("| | Platform | Deal | Coupon | Status |")
        out.append("|:-:|:--|:--|:-:|:-:|")
        out.extend(render_row(d) for d in deals)
        out.append("")
        if cat.get("guide"):
            out.append(f"📖 **[{cat['guide']['text']}]({cat['guide']['url']})**: every code, bundle and saving explained.\n")
        out.append('<p align="right"><a href="#categories">⬆ Back to categories</a></p>\n')
    return "\n".join(out).rstrip() + "\n"


BLOCKS = {
    "STATS": render_stats,
    "NAV": render_nav,
    "TOP-PICKS": render_top_picks,
    "DEALS": render_deals,
}


def build(readme: str, data: dict) -> str:
    for name, fn in BLOCKS.items():
        pattern = re.compile(rf"(<!-- {name}:START -->\n).*?(<!-- {name}:END -->)", re.S)
        if not pattern.search(readme):
            raise SystemExit(f"README.md is missing the <!-- {name}:START/END --> markers")
        content = fn(data).rstrip("\n") + "\n"
        readme = pattern.sub(lambda m: m.group(1) + content + m.group(2), readme)
    return readme


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if README.md is out of date")
    args = parser.parse_args()

    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print("deals.yml has problems:", *errors, sep="\n  - ", file=sys.stderr)
        return 1

    current = README.read_text(encoding="utf-8")
    new = build(current, data)

    if args.check:
        if new != current:
            print("README.md is out of date. Run: python scripts/build_readme.py", file=sys.stderr)
            return 1
        print("README.md is up to date.")
        return 0

    README.write_text(new, encoding="utf-8")
    print(f"README.md rebuilt with {sum(1 for _ in all_deals(data))} deals.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
