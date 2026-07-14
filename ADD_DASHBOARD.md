# Adding a dashboard — quick steps

The site is live at **https://uqabakta.github.io/nem-site/** and rebuilds itself.
To add a dashboard, do these 4 steps.

---

### 1. Copy the file in
Put the finished `.html` into:
```
C:\dev\nem-site\dashboards\static\
```

### 2. Register it in `site.config.json`
Add one entry inside the `dashboards` list:
```json
{
  "slug": "unique-name",
  "title": "Dashboard Title",
  "blurb": "One sentence on what it shows.",
  "tag": "Short label",
  "type": "static",
  "source": "dashboards/static/EXACT_FILENAME.html",
  "cadence": "static"
}
```
JSON rules: entries separated by commas, **no comma after the last one**, list
ends with `]` then `}`. `source` must match the filename exactly.

### 3. Build and preview
```
cd C:\dev\nem-site
conda activate pyomo_env
python build.py
```
Check the count went up (e.g. `7/7 dashboards built`), then:
```
cd dist
python -m http.server 8000
```
Open **http://localhost:8000**, check the new card. `Ctrl+C` to stop, `cd ..`.

### 4. Publish (GitHub Desktop)
1. Open GitHub Desktop — your changes show on the left.
2. Type a summary, e.g. `Add dashboard`.
3. Click **Commit to main**.
4. Click **Push origin**.

Wait 1–2 min, then hard-refresh the live URL (`Ctrl+Shift+R`). Done.

---

**If a card doesn't appear:** the build count didn't go up → JSON typo or the
file wasn't saved/synced.
**If a card shows `[FAIL]`:** the `source` filename doesn't match the actual file.
**Full details:** see `MAINTENANCE.md`.
