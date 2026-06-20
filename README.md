# NEM Analytics site

A static website that hosts public-data NEM dashboards and **rebuilds itself
every day** from AEMO NEMweb, deploying automatically to GitHub Pages. No
server to run, no manual uploads.

The site name and the custom domain are deliberately swappable — pick them
whenever you like and change one config value each.

---

## How it works

```
site.config.json          <- site name, tagline, and the list of dashboards
build.py                  <- assembles everything into dist/
templates/index.template.html  <- landing page (filled in by build.py)
assets/style.css          <- landing page styles
dashboards/
  generators/             <- Python scripts that PRODUCE a dashboard each run
    spike_price.py        <- example (synthetic data; replace with NEMweb)
  static/                 <- standalone HTML files COPIED in as-is
    negative_price_demo.html
.github/workflows/daily-build.yml  <- the daily build + deploy
```

`build.py` reads `site.config.json`, builds each dashboard, renders the landing
page, and writes the finished site to `dist/`. The GitHub Action runs that same
command on a schedule and publishes `dist/` to Pages.

## Run it locally

```bash
pip install -r requirements.txt
python build.py
# open dist/index.html in a browser
```

## Two kinds of dashboard

Register each dashboard in `site.config.json`. There are two types:

**`generated`** — a Python script that's re-run every build. It must expose:

```python
def build(out_path: str) -> None:
    # ... your analysis ...
    fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
```

Porting one of your existing scripts is usually three changes: wrap the body in
`def build(out_path):`, point your final `write_html` at `out_path`, and add an
entry to the config. See `dashboards/generators/spike_price.py`.

**`static`** — a finished HTML file (e.g. a Plotly export) that's just copied
in. Drop it in `dashboards/static/` and point the config at it.

Example config entries:

```json
{ "slug": "spike-price", "title": "Spike Price Analysis",
  "type": "generated", "generator": "dashboards.generators.spike_price",
  "cadence": "daily" }

{ "slug": "negative-price", "title": "Negative Price Analysis",
  "type": "static", "source": "dashboards/static/negative_price_demo.html",
  "cadence": "static" }
```

If a generator fails, the build doesn't crash — the site still deploys and that
one card shows "Rebuilding". So a bad NEMweb day never takes the whole site down.

## Going live (first time)

1. Create a **public** GitHub repo and push these files to `main`.
2. Repo **Settings -> Pages -> Build and deployment -> Source: GitHub Actions**.
3. The workflow runs on push; within a couple of minutes the site is live at
   `https://<your-username>.github.io/<repo-name>/`.
4. You can also trigger it any time from the **Actions** tab ("Run workflow").

## The corporate-proxy note

The daily build runs on GitHub's runners, **not your work machine**, so there's
no Zscaler SSL inspection in the way — your NEMweb fetches hit AEMO directly. If
your fetch code sets proxies or certs for the CS Energy network, guard that
behind an environment check so the same code works in both places:

```python
import os
if os.getenv("CI") != "true":      # only on the work machine, not in Actions
    session.proxies = {...}
    session.verify = "/path/to/zscaler-root.crt"
```

GitHub Actions sets `CI=true` automatically.

## Adding your .com.au domain later

When your domain is registered, set it in `site.config.json`:

```json
"custom_domain": "yourdomain.com.au"
```

The next build emits a `CNAME` file automatically. Then at your domain
registrar, point the DNS at GitHub Pages (a `CNAME`/`ALIAS` record to
`<your-username>.github.io`, or the four Pages `A` records for an apex domain —
GitHub's Pages docs list the current IPs). Nothing else changes; the same site
just answers on the new address. Leave `custom_domain` empty until then.

## Renaming the site

Change `site.name` (and tagline/intro) in `site.config.json`. That's the only
place the name lives.
