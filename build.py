#!/usr/bin/env python3
"""
Build the static site into ./dist.

Reads site.config.json, then for each dashboard:
  - type "generated": imports the named module and calls its build(out_path)
  - type "static":    copies the source HTML into the site as-is

Finally renders the landing page from templates/index.template.html and copies
assets/. Run locally with `python build.py`; the GitHub Action runs the same
command every day and deploys the result to GitHub Pages.

Designed to be dependency-light: only the standard library is needed to build
the site shell. Individual generators pull in whatever they need
(plotly/pandas/etc) via requirements.txt.
"""

from __future__ import annotations

import datetime as _dt
import html
import importlib
import json
import shutil
import sys
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent.resolve()
DIST = ROOT / "dist"
CONFIG = ROOT / "site.config.json"
TEMPLATE = ROOT / "templates" / "index.template.html"
ASSETS = ROOT / "assets"

BRISBANE = ZoneInfo("Australia/Brisbane")


def load_config() -> dict:
    with open(CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


def clean_dist() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "dashboards").mkdir(parents=True)


def copy_assets() -> None:
    if ASSETS.exists():
        shutil.copytree(ASSETS, DIST / "assets")


def inject_back_nav(out_path: Path, site_name: str) -> None:
    """Insert a 'back to dashboards' bar at the top of a dashboard page.

    Each dashboard is a standalone HTML page (your Plotly export), so on its own
    it has no link home. We splice a slim sticky bar in right after <body>,
    styled to match the landing page (same fonts, paper background, accent on
    hover). Done here in the build so you never edit individual dashboards and it
    applies automatically to every dashboard, now and later.
    """
    name = html.escape(site_name)
    bar = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@700&family=JetBrains+Mono:wght@400;500&display=swap');
.nemnav {{
  position: sticky; top: 0; z-index: 99999;
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 12px 20px;
  background: #FAFAF7; border-bottom: 1px solid #E4E4DC;
  font-family: 'JetBrains Mono', monospace; font-size: 13px;
}}
.nemnav a {{ color: #6B7280; text-decoration: none; transition: color .15s ease; }}
.nemnav a:hover {{ color: #E8743B; }}
.nemnav__home {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 15px; color: #14181B; }}
</style>
<nav class="nemnav">
  <a href="../index.html">&larr; Back to dashboards</a>
  <span class="nemnav__home">{name}</span>
</nav>
"""
    try:
        text = out_path.read_text(encoding="utf-8")
        lower = text.lower()
        idx = lower.find("<body")
        if idx != -1:
            close = text.find(">", idx)
            if close != -1:
                text = text[: close + 1] + "\n" + bar + text[close + 1 :]
            else:
                text = bar + text
        else:
            text = bar + text
        out_path.write_text(text, encoding="utf-8")
    except Exception:  # noqa: BLE001 - cosmetic; never fail the build over it
        print(f"  [warn] could not add back-nav to {out_path.name}")


def build_dashboard(dash: dict, site_name: str) -> dict:
    """Produce one dashboard's HTML in dist/dashboards/<slug>.html.

    Returns the dashboard dict annotated with build status so the landing
    page can show which ones succeeded. A failing generator never breaks the
    whole build â€” the site still deploys, with that card marked unavailable.
    """
    slug = dash["slug"]
    out_path = DIST / "dashboards" / f"{slug}.html"
    dash = dict(dash)  # copy so we can annotate

    try:
        if dash["type"] == "generated":
            module = importlib.import_module(dash["generator"])
            module.build(str(out_path))
        elif dash["type"] == "static":
            src = ROOT / dash["source"]
            if not src.exists():
                raise FileNotFoundError(f"static source missing: {src}")
            shutil.copyfile(src, out_path)
        else:
            raise ValueError(f"unknown dashboard type: {dash['type']!r}")

        if not out_path.exists():
            raise RuntimeError("generator ran but produced no output file")

        inject_back_nav(out_path, site_name)
        dash["ok"] = True
        print(f"  [ok]   {slug}  ->  dashboards/{slug}.html")
    except Exception:  # noqa: BLE001 - we deliberately keep building
        dash["ok"] = False
        print(f"  [FAIL] {slug}")
        traceback.print_exc()

    return dash


def render_cards(dashboards: list[dict]) -> str:
    cards = []
    for d in dashboards:
        title = html.escape(d["title"])
        blurb = html.escape(d.get("blurb", ""))
        tag = html.escape(d.get("tag", ""))
        cadence = d.get("cadence", "static")
        ok = d.get("ok", False)
        href = f"dashboards/{d['slug']}.html"

        badge_label = {"daily": "Updated daily", "static": "Static"}.get(cadence, cadence)
        badge_class = "badge--live" if cadence == "daily" else "badge--static"

        if ok:
            card = f"""        <a class="card" href="{href}">
          <span class="card__tag">{tag}</span>
          <h3 class="card__title">{title}</h3>
          <p class="card__blurb">{blurb}</p>
          <span class="badge {badge_class}">{badge_label}</span>
        </a>"""
        else:
            card = f"""        <div class="card card--down" aria-disabled="true">
          <span class="card__tag">{tag}</span>
          <h3 class="card__title">{title}</h3>
          <p class="card__blurb">{blurb}</p>
          <span class="badge badge--down">Rebuilding &mdash; check back soon</span>
        </div>"""
        cards.append(card)
    return "\n".join(cards)


def render_index(config: dict, dashboards: list[dict]) -> None:
    site = config["site"]
    now = _dt.datetime.now(BRISBANE)
    stamp = now.strftime("%d %b %Y, %H:%M") + " AEST"

    with open(TEMPLATE, encoding="utf-8") as fh:
        tmpl = fh.read()

    replacements = {
        "{{SITE_NAME}}": html.escape(site["name"]),
        "{{TAGLINE}}": html.escape(site["tagline"]),
        "{{INTRO}}": html.escape(site["intro"]),
        "{{AUTHOR}}": html.escape(site["author"]),
        "{{FOOTER_NOTE}}": html.escape(site["footer_note"]),
        "{{BUILD_DATE}}": stamp,
        "{{YEAR}}": str(now.year),
        "{{DASHBOARD_CARDS}}": render_cards(dashboards),
        "{{DASHBOARD_COUNT}}": str(sum(1 for d in dashboards if d.get("ok"))),
    }
    for key, val in replacements.items():
        tmpl = tmpl.replace(key, val)

    (DIST / "index.html").write_text(tmpl, encoding="utf-8")
    print(f"  [ok]   index.html  ({stamp})")


def write_custom_domain(config: dict) -> None:
    """If a custom domain is set in config, emit a CNAME file so GitHub Pages
    serves the site there. Leave custom_domain empty until your .com.au is
    registered â€” then just fill it in and the next build wires it up."""
    domain = config["site"].get("custom_domain", "").strip()
    if domain:
        (DIST / "CNAME").write_text(domain + "\n", encoding="utf-8")
        print(f"  [ok]   CNAME -> {domain}")
    # .nojekyll: stop GitHub Pages' Jekyll from touching our files
    (DIST / ".nojekyll").touch()


def main() -> int:
    print("Building site ...")
    config = load_config()
    clean_dist()
    copy_assets()

    site_name = config["site"]["name"]
    built = [build_dashboard(d, site_name) for d in config["dashboards"]]
    render_index(config, built)
    write_custom_domain(config)

    n_ok = sum(1 for d in built if d.get("ok"))
    n_total = len(built)
    print(f"Done. {n_ok}/{n_total} dashboards built. Output in ./dist")

    # Don't fail the deploy just because one dashboard broke; the site should
    # still go live. Only hard-fail if literally nothing built.
    return 0 if (n_ok > 0 or n_total == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
