#!/usr/bin/env python3
"""Build the static site into ./dist. See README.md for full docs."""

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

# Cloudflare Web Analytics beacon — injected into every page
CF_ANALYTICS = (
    '<!-- Cloudflare Web Analytics -->'
    '<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
    'data-cf-beacon=\'{"token": "2c2a3ff0e7234e12a6f6a5cc9baf3486"}\'></script>'
    '<!-- End Cloudflare Web Analytics -->'
)


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


def humanize_slug(slug: str) -> str:
    """Turn a slug into a short nav label, e.g. 'market-shift' -> 'Market Shift'."""
    special = {"index": "Overview", "bess": "BESS", "vre-curtailment": "VRE Curtailment"}
    if slug in special:
        return special[slug]
    return slug.replace("-", " ").replace("_", " ").title()


def inject_dashboard_utility_bar(
    out_path: Path, site_name: str, contact_email: str, all_dashboards: list[dict], current_slug: str
) -> None:
    """Insert a slim, self-contained nav bar at the top of a dashboard page.

    This bar is generated fresh from site.config.json on every build, so it can
    never go stale the way a hand-built internal nav can. It links to every
    other configured dashboard (auto-labelled from each slug), highlights
    whichever page you're currently on, and tucks Contact/Feedback/Disclaimer
    at the end. Dashboards keep whatever internal nav they already have in
    their own exported HTML (untouched, further down the page) â€” this bar
    simply sits above it as the authoritative, always-correct way to get
    around the site.
    """
    name = html.escape(site_name)
    email = contact_email.strip()

    tabs = []
    for d in all_dashboards:
        if not d.get("ok"):
            continue
        label = html.escape(humanize_slug(d["slug"]))
        cls = "ergonav__tab active" if d["slug"] == current_slug else "ergonav__tab"
        tabs.append(f'<a class="{cls}" href="{d["slug"]}.html">{label}</a>')
    tabs_html = "".join(tabs)

    contact_links = ""
    if email:
        from urllib.parse import quote
        subject = quote(f"Feedback on {site_name} dashboard")
        contact_links = (
            f'<a href="mailto:{html.escape(email)}">Contact</a>'
            f'<a href="mailto:{html.escape(email)}?subject={subject}">Feedback</a>'
        )

    bar = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
.ergonav {{
  position: sticky; top: 0; z-index: 99999;
  display: flex; align-items: center;
  gap: 18px; padding: 10px 18px;
  background: #0d1015; border-bottom: 1px solid #232a35;
  font-family: 'JetBrains Mono', monospace; font-size: 12.5px;
}}
.ergonav__home {{ color: #e8ecf1; font-weight: 500; text-decoration: none; flex-shrink: 0; }}
.ergonav__home:hover {{ color: #2dd4bf; }}
.ergonav__tabs {{
  display: flex; gap: 16px; flex: 1; min-width: 0;
  overflow-x: auto; white-space: nowrap; scrollbar-width: thin;
}}
.ergonav__tab {{ color: #6f7887; text-decoration: none; padding-bottom: 2px; border-bottom: 2px solid transparent; transition: color .15s ease; }}
.ergonav__tab:hover {{ color: #2dd4bf; }}
.ergonav__tab.active {{ color: #e8ecf1; border-bottom-color: #2dd4bf; }}
.ergonav__links {{ display: flex; gap: 16px; flex-shrink: 0; }}
.ergonav__links a {{ color: #6f7887; text-decoration: none; transition: color .15s ease; }}
.ergonav__links a:hover {{ color: #2dd4bf; }}
</style>
<nav class="ergonav">
  <a class="ergonav__home" href="../index.html">&larr; {name}</a>
  <div class="ergonav__tabs">{tabs_html}</div>
  <div class="ergonav__links">
    {contact_links}<a href="../disclaimer.html">Disclaimer</a>
  </div>
</nav>
"""
    try:
        text = out_path.read_text(encoding="utf-8")
        lower = text.lower()
        idx = lower.find("<body")
        if idx != -1:
            close = text.find(">", idx)
            text = text[: close + 1] + "\n" + CF_ANALYTICS + bar + text[close + 1 :] if close != -1 else CF_ANALYTICS + bar + text
        else:
            text = CF_ANALYTICS + bar + text
        out_path.write_text(text, encoding="utf-8")
    except Exception:
        print(f"  [warn] could not add utility bar to {out_path.name}")


def build_dashboard(dash: dict) -> dict:
    slug = dash["slug"]
    out_path = DIST / "dashboards" / f"{slug}.html"
    dash = dict(dash)
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
        dash["ok"] = True
        print(f"  [ok]   {slug}  ->  dashboards/{slug}.html")
    except Exception:
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
        badge_label = {"daily": "Updated daily", "6h": "Updated every 6 hours",
                       "hourly": "Updated hourly", "static": "Static"}.get(cadence, cadence)
        badge_class = ("badge--live" if cadence in {"daily", "6h", "hourly"}
                       else "badge--static")
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


def site_level_replacements(config: dict) -> dict:
    """Replacements shared by every page: brand, footer, contact column."""
    site = config["site"]
    now = _dt.datetime.now(BRISBANE)
    stamp = now.strftime("%d %b %Y, %H:%M") + " AEST"

    contact_email = site.get("contact_email", "").strip()
    if contact_email:
        contact_column = (
            '      <div class="foot__col">\n'
            "        <h4>Contact</h4>\n"
            f'        <a href="mailto:{html.escape(contact_email)}">{html.escape(contact_email)}</a>\n'
            "      </div>"
        )
        foot_grid_class = ""
    else:
        contact_column = ""
        foot_grid_class = " foot__inner--2col"

    return {
        "{{CF_ANALYTICS}}": CF_ANALYTICS,
        "{{SITE_NAME}}": html.escape(site["name"]),
        "{{AUTHOR}}": html.escape(site["author"]),
        "{{FOOTER_NOTE}}": html.escape(site["footer_note"]),
        "{{BUILD_DATE}}": stamp,
        "{{YEAR}}": str(now.year),
        "{{CONTACT_COLUMN_HTML}}": contact_column,
        "{{FOOT_GRID_CLASS}}": foot_grid_class,
    }


def render_index(config: dict, dashboards: list[dict]) -> None:
    site = config["site"]

    with open(TEMPLATE, encoding="utf-8") as fh:
        tmpl = fh.read()

    replacements = site_level_replacements(config)
    replacements.update({
        "{{TAGLINE}}": html.escape(site["tagline"]),
        "{{INTRO}}": html.escape(site["intro"]),
        "{{DASHBOARD_CARDS}}": render_cards(dashboards),
        "{{DASHBOARD_COUNT}}": str(sum(1 for d in dashboards if d.get("ok"))),
    })
    for key, val in replacements.items():
        tmpl = tmpl.replace(key, val)

    (DIST / "index.html").write_text(tmpl, encoding="utf-8")
    print(f"  [ok]   index.html  ({replacements['{{BUILD_DATE}}']})")


def render_legal_page(config: dict, out_name: str, page_title: str, content_file: str) -> None:
    """Render a simple content page (e.g. disclaimer.html) using the shared
    nav/footer shell. Body copy lives in its own editable HTML fragment under
    templates/, so wording can be updated without touching this script."""
    shell_path = ROOT / "templates" / "legal.template.html"
    content_path = ROOT / "templates" / content_file
    if not shell_path.exists() or not content_path.exists():
        print(f"  [warn] skipping {out_name}: template or content file missing")
        return

    tmpl = shell_path.read_text(encoding="utf-8")
    body = content_path.read_text(encoding="utf-8")

    replacements = site_level_replacements(config)
    # The content fragment may itself reference {{SITE_NAME}}, so resolve it first.
    for key, val in replacements.items():
        body = body.replace(key, val)

    replacements.update({
        "{{PAGE_TITLE}}": html.escape(page_title),
        "{{BODY_CONTENT}}": body,
    })
    for key, val in replacements.items():
        tmpl = tmpl.replace(key, val)

    (DIST / out_name).write_text(tmpl, encoding="utf-8")
    print(f"  [ok]   {out_name}")


def write_custom_domain(config: dict) -> None:
    domain = config["site"].get("custom_domain", "").strip()
    if domain:
        (DIST / "CNAME").write_text(domain + "\n", encoding="utf-8")
        print(f"  [ok]   CNAME -> {domain}")
    (DIST / ".nojekyll").touch()

def write_sitemap(config: dict, dashboards: list[dict]) -> None:
    domain = config["site"].get("custom_domain", "").strip()
    if not domain:
        return
    base = f"https://{domain}"
    urls = [
        (f"{base}/", "daily", "1.0"),
        (f"{base}/about.html", "monthly", "0.5"),
        (f"{base}/disclaimer.html", "monthly", "0.3"),
    ]
    for d in dashboards:
        if d.get("ok"):
            urls.append((f"{base}/dashboards/{d['slug']}.html", "daily", "0.8"))

    entries = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        for loc, freq, prio in urls
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    (DIST / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"  [ok]   sitemap.xml  ({len(urls)} URLs)")

def main() -> int:
    print("Building site ...")
    config = load_config()
    clean_dist()
    copy_assets()
    site_name = config["site"]["name"]
    contact_email = config["site"].get("contact_email", "").strip()

    built = [build_dashboard(d) for d in config["dashboards"]]

    # Second pass: now that we know which dashboards actually built, inject a
    # nav bar into each successful one linking to every other dashboard.
    for dash in built:
        if dash.get("ok"):
            out_path = DIST / "dashboards" / f"{dash['slug']}.html"
            inject_dashboard_utility_bar(out_path, site_name, contact_email, built, dash["slug"])

    render_index(config, built)
    render_legal_page(config, "disclaimer.html", "Disclaimer", "disclaimer_content.html")
    render_legal_page(config, "about.html", "About", "about_content.html")
    write_custom_domain(config)
    write_sitemap(config, built)
    n_ok = sum(1 for d in built if d.get("ok"))
    n_total = len(built)
    print(f"Done. {n_ok}/{n_total} dashboards built. Output in ./dist")
    return 0 if (n_ok > 0 or n_total == 0) else 1


if __name__ == "__main__":
    sys.exit(main())