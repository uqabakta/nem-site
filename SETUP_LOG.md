# Ergodic Analytics — setup log & runbook

A record of how this site and business were set up, in order, with the gotchas
that cost time. Written so future-you (or someone else) can rebuild, debug, or
migrate any part of it without rediscovering everything the hard way.

> **This repo is public.** Never put the ABN, personal name, personal email
> addresses, API keys, or SMTP credentials in this file or anywhere else in the
> repo. Placeholders are used below where secrets belong.

---

## 1. What this is

A static website publishing public-data NEM analytics dashboards, rebuilt
automatically every day, served on a custom domain, with a working business
email address. Built and run at effectively zero ongoing cost beyond the domain.

**Live at:** https://ergodicanalytics.com.au
**Fallback URL:** https://uqabakta.github.io/nem-site/ (always works, useful for
diagnosing whether a problem is the site or the domain/DNS)

---

## 2. The stack

```
  Pipeline (local)              Site repo (local)           Cloud
  ────────────────              ─────────────────           ─────
  main.py                       C:\dev\nem-site
    ├─ downloads AEMO data        ├─ site.config.json       GitHub repo
    ├─ runs analysis              ├─ build.py          →    └─ GitHub Actions
    ├─ writes dashboard/*.html    ├─ templates/                 └─ GitHub Pages
    └─ copies HTML  ─────────→    ├─ assets/                          │
                                  └─ dashboards/static/               ▼
                                                              Cloudflare DNS
                                                                     │
                                                                     ▼
                                                          ergodicanalytics.com.au
```

Two separate systems that meet at one folder:

1. **`main.py` pipeline** (in OneDrive, `NEM_Dashboards/`) — downloads AEMO data,
   runs the analysis, produces dashboard HTML. At the end it copies every
   `.html` into `C:\dev\nem-site\dashboards\static\` automatically.
2. **The site repo** (`C:\dev\nem-site`) — `build.py` assembles those dashboards
   plus a landing page, About page and disclaimer into `dist/`, which GitHub
   Actions publishes to GitHub Pages.

---

## 3. Business setup (done, in this order — the order matters)

Sequence is forced by dependencies: **ABN → business name → .com.au domain**.

1. **ABN** — applied via the Australian Business Register (abr.gov.au). Free.
   Sole trader, so the ABN is registered to the individual, not the trading name.
2. **Business name "Ergodic Analytics"** — registered with ASIC. Requires the ABN.
   $45/yr or $105/3yr. Checked availability on ASIC first (came back clear).
3. **Domain `ergodicanalytics.com.au`** — VentraIP, ~$10–30/yr. `.com.au` requires
   an ABN at checkout, which is why it comes last.

**Privacy note on the ASIC address fields** (this tripped us up):
- *Principal place of business* — must be a physical address, but for an
  individual business-name holder ASIC only publishes **suburb, state,
  postcode**. Home address is fine; the street address is not shown.
- *Address for service of documents* — **fully public, no suppression**, but a
  **PO Box is accepted**. Use a PO Box or an accountant's address here.

**Not done / not needed yet:** GST registration (only required above $75k
turnover), Pty Ltd company (overkill), IP Australia trade mark check on the name
(ASIC clear ≠ trademark clear — worth doing before investing further in the name).

---

## 4. Repo and hosting

1. Repo lives at **`C:\dev\nem-site`** — deliberately moved **out of the UQ
   OneDrive**. Two reasons: OneDrive and Git fight over the same folder, and a
   commercial business shouldn't live in institutional storage that can be
   deprovisioned.
2. Public GitHub repo `uqabakta/nem-site`, pushed via **GitHub Desktop**
   (avoids the personal-access-token dance that command-line `git push` needs).
3. **Settings → Pages → Source: GitHub Actions** (not "Deploy from a branch").
4. **Settings → Actions → General → Workflow permissions: Read and write.**
5. `.github/workflows/daily-build.yml` runs `python build.py` and deploys —
   on every push, and daily at 20:00 UTC (06:00 Brisbane).

**Personal account for now.** When/if a company GitHub Organization is created,
"Transfer ownership" moves the repo across with full history and auto-redirects
the old URL. Nothing is lost by starting personal.

---

## 5. DNS (Cloudflare)

Domain is registered at **VentraIP** but DNS is served by **Cloudflare** (free plan).

**Nameservers** (set in VentraIP → Manage DNS → Custom Nameservers):
```
agustin.ns.cloudflare.com
sneh.ns.cloudflare.com
```
Switching to custom nameservers **removes VentraIP's own DNS records after 72
hours** — that's expected. Cloudflare is authoritative now; VentraIP's DNS
Hosting tab is irrelevant and should not be re-populated.

**Records in Cloudflare → DNS → Records:**

| Type  | Name                 | Content                                    | Proxy    |
|-------|----------------------|--------------------------------------------|----------|
| A     | `ergodicanalytics.com.au` | `185.199.108.153`                     | DNS only |
| A     | `ergodicanalytics.com.au` | `185.199.109.153`                     | DNS only |
| A     | `ergodicanalytics.com.au` | `185.199.110.153`                     | DNS only |
| A     | `ergodicanalytics.com.au` | `185.199.111.153`                     | DNS only |
| CNAME | `www`                | `uqabakta.github.io`                       | DNS only |
| MX    | `@` (×3)             | `route1/2/3.mx.cloudflare.net`             | —        |
| TXT   | `@`                  | `v=spf1 include:_spf.mx.cloudflare.net ~all` | —      |
| TXT   | `@`                  | `brevo-code:…`                             | —        |
| CNAME | `brevo1._domainkey`  | `b1.ergodicanalytics-com-au.dkim.brevo.com` | DNS only |
| CNAME | `brevo2._domainkey`  | `b2.ergodicanalytics-com-au.dkim.brevo.com` | DNS only |
| CNAME | `mail`               | `mail-ergodicanalytics-com-au.brand.brevosend.com` | DNS only |
| CNAME | `img.mail`           | `…img.brand.brevosend.com`                 | DNS only |
| CNAME | `r.mail`             | `…r.brand.brevosend.com`                   | DNS only |

**CRITICAL: the GitHub Pages records must be "DNS only" (grey cloud), never
"Proxied" (orange).** Cloudflare will repeatedly nag with a yellow "Proxying is
required for most security and performance features" banner and a "Proxy DNS
records" warning badge. **Ignore both.** Proxying in front of GitHub Pages breaks
the SSL certificate and reproduces the `NET::ERR_CERT_COMMON_NAME_INVALID` error.

**The custom domain also has to be set in two places:**
1. `site.config.json` → `"custom_domain": "ergodicanalytics.com.au"` — makes
   `build.py` emit a `CNAME` file into `dist/`.
2. **GitHub → Settings → Pages → Custom domain** field. This one is easy to miss.
   Without it, GitHub serves its default `*.github.io` certificate and every
   visitor gets a browser security warning. After saving, wait for "DNS check
   successful", then tick **Enforce HTTPS** once it becomes clickable.

---

## 6. Email

Two halves, two different services, because **Cloudflare Email Routing can only
receive — it has no outbound SMTP at all.**

### Receiving — Cloudflare Email Routing (free)
- Cloudflare → Email → Email Routing
- Destination address: personal Gmail, verified once
- Routing rule: `contact@ergodicanalytics.com.au` → that Gmail
- Catch-all rule: Drop (leave as-is)
- There is no mailbox to "create" — the rule *is* the address.

### Sending — Brevo SMTP relay (free tier, 300/day) + Gmail "Send mail as"
- Brevo account, domain `ergodicanalytics.com.au` added and **fully authenticated**
- Brevo → Settings → SMTP & API → generate an SMTP key (shown once — copy it)
- Gmail → Settings → Accounts and Import → Send mail as → Add another email address:
  - Name: `Ergodic Analytics`, Email: `contact@ergodicanalytics.com.au`
  - Treat as an alias: ✅
  - **SMTP Server:** `smtp-relay.brevo.com`  **Port:** `587`  **TLS**
  - **Username:** the Brevo SMTP login (`…@smtp-brevo.com`) — *not* the domain address
  - **Password:** the Brevo SMTP key
- Gmail sends a verification link to `contact@…`, which arrives via the Cloudflare
  forwarding. Click it.

**Gmail will auto-fill `route1.mx.cloudflare.net` as the SMTP server. That is
wrong** — it's Cloudflare's *inbound* server. Overwrite it with Brevo's.

**Two separate Brevo requirements, both mandatory:**
1. `contact@ergodicanalytics.com.au` must exist as a **verified sender**
   (Settings → Senders, domains, IPs → Senders → Add sender), or Brevo rejects
   with *"the sender you used … is not valid"*.
2. The **domain must be fully authenticated** — *all* the CNAMEs, including the
   branded/redirection ones (`mail`, `img.mail`, `r.mail`) that look optional.
   Without full authentication Brevo silently sends from `@…brevosend.com` with
   your address only as reply-to, which defeats the entire point.

---

## 7. Daily workflow

```powershell
# 1. Regenerate dashboards (auto-copies them into the site repo)
python main.py                 # or: python main.py --skip-download

# 2. Rebuild the site
cd C:\dev\nem-site
conda activate pyomo_env
python build.py                # want: all dashboards [ok], index.html, disclaimer.html, about.html

# 3. Preview
cd dist
python -m http.server 8000     # open http://localhost:8000 ; Ctrl+C to stop
cd ..

# 4. Publish — GitHub Desktop: Commit to main → Push origin
```

GitHub Actions rebuilds and redeploys automatically. Also runs daily on its own
schedule, so dashboards refresh without any of the above.

See `MAINTENANCE.md` and `ADD_DASHBOARD.md` for the detailed versions.

---

## 8. Gotchas — the things that actually cost hours

**`slug` must exactly match the source filename (minus `.html`).**
`bess.html` → `"slug": "bess"`. Not cosmetic: each dashboard's own internal tab
bar (baked into the exported HTML by `main.py`) links to sibling files by their
original names. If the slug differs, `build.py` renames the file on copy and
every internal link 404s.

**JSON is unforgiving.** A doubled `]` or a missing/trailing comma in
`site.config.json` produces cryptic errors like `Extra data: line 1 column 13`.
Validate before building:
```powershell
python -c "import json; json.load(open('site.config.json')); print('Valid JSON')"
```
When a paste goes wrong, replace the **whole file** rather than merging edits.

**PowerShell quoting.** `findstr "\"slug\": \"index\"" file` fails. Use
`Select-String -Path site.config.json -Pattern 'slug.*index'` instead.

**Partial file copies are the #1 source of "it's not working".** Several rounds
were lost to a `style.css` or `build.py` that never actually landed in the repo.
Verify before rebuilding:
```powershell
Select-String -Path assets\style.css -Pattern '0d1015'    # dark theme present?
Select-String -Path build.py -Pattern 'ergonav__tabs'     # current build.py?
```

**Cloudflare Email Routing set up while the zone was still "pending" silently
failed to write its MX/TXT records into the live zone.** The Email Routing
settings page showed them as "Locked" (i.e. configured), but `DNS → Records`
didn't list them and external lookups (Google DNS, MXToolbox) returned nothing.
Fix: add the MX + SPF records to the zone **manually**. Symptoms of this bug:
empty Activity Log, "Routing status: Disabled", tooltip "service is not
configured", no mail arriving. A matching community report existed, so it's a
known platform issue, not a misconfiguration.

**"Routing status: Disabled" can be cosmetic.** Mail delivered fine while the
badge stayed red. Trust the Analytics counters and the Activity Log over the badge.

**Zoho Mail's free tier is not offered in Australia** — the pricing page shows
only paid plans (cheapest Mail Lite ≈ A$20/yr). Several guides claiming a free
5-user tier are region-specific or outdated.

**Gmail deduplicates mail you send to yourself**, so a test from your own Gmail
to `contact@…` (which forwards back to that same Gmail) can appear to vanish.
Test with a different address.

**Brevo's free tier shares a sending domain**, which Gmail rate-limits
(`421-4.7.28 … unusual rate of mail … temporarily rate limited`). Deferred, not
failed — it retries. If this becomes a recurring problem, the escape hatch is a
real mailbox (Zoho Mail Lite ≈ A$20/yr) instead of a relay.

**DNS propagation is real.** Almost every "it's broken" moment in this build was
actually "wait 15 more minutes". Check with:
```
https://dns.google/resolve?name=ergodicanalytics.com.au&type=MX
```
An `"Answer"` section = propagated. Only `"Authority"` with an SOA = genuinely no
record. Note that a cached *negative* answer also has a TTL, so a fix can take up
to ~30 min to become visible even when it's already correct.

---

## 9. Costs

| Item | Cost |
|---|---|
| ABN | free |
| ASIC business name | $45/yr (or $105/3yr) |
| Domain `.com.au` (VentraIP) | ~$10–30/yr, auto-renew on |
| GitHub (public repo, Pages, Actions) | free |
| Cloudflare (DNS + Email Routing) | free |
| Brevo (SMTP relay, 300 emails/day) | free |
| **Ongoing total** | **~$30–45/yr** |

The `.online` domain bundled free with the `.com.au` has auto-renew **off** — it
will simply expire. Leave it.

---

## 10. Outstanding / ideas

- **Homepage copy** — says *what* and *why*, never says **who it's for**
  (traders? analysts? prospective consulting clients?). Worth sharpening.
- **Blog** — nothing for Google to index but the homepage right now. Biggest
  single lever for search visibility, and the largest piece of work.
- **Google Search Console** — verify via the HTML-tag method (URL prefix
  property), not DNS, and request indexing. Nothing indexed yet.
- **More frequent rebuilds (every 2–4h)** — the *site* rebuild is a one-line cron
  change in `daily-build.yml`. The **`main.py` pipeline** is the hard part: it has
  local dependencies and can't trivially move to GitHub's runners. Realistic
  answer is Windows Task Scheduler locally, not a cloud migration.
- **IP Australia trade mark search** on "Ergodic Analytics" — ASIC clear is not
  the same as trademark clear.
- **Dashboards' own internal nav** still says "NEM Analytics" (baked into the
  exports by `main.py`). The site's injected bar is authoritative now; the
  pipeline's `_inject_nav` is commented out. Worth renaming at the source
  eventually.
