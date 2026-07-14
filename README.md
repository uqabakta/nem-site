# Ergodic Analytics site

A static website of public-data NEM dashboards that **rebuilds itself every
day** from AEMO NEMweb, deploying automatically to GitHub Pages at
[ergodicanalytics.com.au](https://ergodicanalytics.com.au). No server to run,
no manual uploads.

> Looking for the plain-language "how do I update the site" guide instead?
> See `MAINTENANCE.md` and `ADD_DASHBOARD.md`. This file is the technical
> reference for how the build system works.

---

## How it works

```
site.config.json                     <- site name, tagline, and the list of dashboards
build.py                             <- assembles everything into dist/
templates/index.template.html        <- landing page (filled in by build.py)
templates/legal.template.html        <- shell for content pages (disclaimer, etc.)
templates/disclaimer_content.html    <- the disclaimer's actual wording (editable)
assets/style.css                     <- site-wide styles (dark theme)
assets/favicon.svg                   <- browser tab icon
dashboards/
  static/                            <- your exported dashboard HTML files
    index.html, bess.html, wind.html, solar.html, market-shift.html,
    curtailment.html, optimizer.html
.github/workflows/daily-build.yml    <- the daily scheduled build + deploy
```

`build.py` reads `site.config.json`, copies/builds each dashboard, injects a
navigation bar into each one, renders the landing page and disclaimer page,
and writes the finished site to `dist/`. The GitHub Action runs that same
command daily and publishes `dist/` to Pages.

## Run it locally

```bash
pip install -r requirements.txt
python build.py
cd dist
python -m http.server 8000
# open http://localhost:8000
```

## The dashboards

All current dashboards are `type: "static"` — finished HTML files you export
yourself and drop into `dashboards/static/`, registered in `site.config.json`:

```json
{ "slug": "bess", "title": "BESS Performance in NEM",
  "blurb": "Dispatch behaviour and performance profile of grid-scale batteries.",
  "tag": "NEM BESS fleet", "type": "static",
  "source": "dashboards/static/bess.html", "cadence": "static" }
```

**Critical rule: `slug` must exactly match the source filename (without
`.html`).** For example `bess.html` → slug `"bess"`, `market-shift.html` →
slug `"market-shift"`. This isn't cosmetic — each dashboard's own internal
cross-links (the Overview/Market Shift/BESS/... tabs your dashboards already
have baked in) point to sibling files by their original names. If the slug
doesn't match, `build.py` renames the file on copy and those internal links
404. Keeping slug = filename stem keeps everything wired together correctly.

A `type: "generated"` option also exists for dashboards built by a Python
script at build time (see `dashboards/generators/` for the pattern: a module
exposing `build(out_path)`), useful later if you want a dashboard that pulls
fresh NEMweb data on every scheduled run rather than being a static export.

If a dashboard fails to build, the whole site still deploys — that one card
just shows "Rebuilding" on the homepage instead of crashing everything.

## Navigation bar on every dashboard

`build.py` injects a slim dark bar at the top of every dashboard page,
generated fresh from `site.config.json` on every build:

- **← Ergodic Analytics** — back to the homepage
- **Tabs for every configured dashboard** (auto-labelled from each slug, e.g.
  `market-shift` → "Market Shift"), with the current page highlighted
- **Contact** / **Feedback** (mailto links — only shown if `contact_email` is
  set in config) and **Disclaimer**

This bar is intentionally the *authoritative* source of navigation — it can
never go stale, because it's regenerated from config every time, unlike a
hand-built internal nav that has to be manually kept in sync.

## The disclaimer page

`build.py` also renders `disclaimer.html` using `templates/legal.template.html`
(the shared nav/footer shell) plus `templates/disclaimer_content.html` (the
actual wording). Edit the wording file directly — no Python required — and it
picks up `{{SITE_NAME}}` automatically if referenced.

## Site-wide config (`site.config.json`)

| Key | Purpose |
|---|---|
| `name` | Site name, shown in nav/footer/page titles |
| `tagline`, `intro` | Homepage hero copy |
| `author` | Shown in the footer credit line |
| `footer_note` | Small print in the footer |
| `custom_domain` | If set, `build.py` writes a `CNAME` file for GitHub Pages |
| `contact_email` | If set, enables Contact/Feedback links site-wide |

## Theme

The whole site (homepage, disclaimer page, and the injected dashboard nav bar)
shares one dark palette, defined as CSS variables at the top of
`assets/style.css` (`--paper`, `--panel`, `--ink`, `--accent`, etc.). The
injected dashboard bar can't read that stylesheet (dashboards are standalone
files), so its colors are hardcoded to match — if you ever change the palette
in `style.css`, update the matching hex values in
`inject_dashboard_utility_bar()` in `build.py` too.

## Going live / updating

See `MAINTENANCE.md` for the day-to-day workflow (edit → build → preview →
commit → push) and `ADD_DASHBOARD.md` for the quick add-a-dashboard steps.

## The corporate-proxy note

The daily build runs on GitHub's own runners, not your work machine, so there's
no Zscaler SSL inspection involved — any NEMweb fetch code in a `generated`
dashboard hits AEMO directly. GitHub Actions sets `CI=true` automatically if
you ever need to branch on that.
