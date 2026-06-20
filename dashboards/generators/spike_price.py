"""
Spike Price Analysis â€” EXAMPLE GENERATOR.

This is the contract every script-based dashboard follows: expose a single
function

    build(out_path: str) -> None

that writes ONE self-contained HTML file to out_path. The build orchestrator
imports this module and calls build() once per daily run.

----------------------------------------------------------------------------
THIS VERSION USES SYNTHETIC DATA so the site builds on day one, in CI, with no
AEMO access required. To make it real, replace `load_data()` with your actual
NEMweb pull (DispatchIS_Reports for RRP, etc.). Everything below the data layer
â€” the plotting, the write_html â€” can stay almost as-is.

Porting one of your existing scripts is usually just:
  1. wrap your script body in `def build(out_path):`
  2. change your final `fig.write_html("whatever.html")` to
     `fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)`
  3. register it in site.config.json with type "generated"

NOTE ON THE CORPORATE PROXY: this runs on GitHub's runners, NOT your work
machine, so there's no Zscaler SSL inspection in the way. If your fetch code
sets proxies/certs for the CS Energy network, guard that behind an env check
(e.g. `if os.getenv("CI") != "true": ...`) so the same file works in both
places.
----------------------------------------------------------------------------
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REGIONS = ["QLD1", "NSW1", "VIC1", "SA1", "TAS1"]
SPIKE_THRESHOLD = 300.0  # $/MWh
PRICE_CAP = 16600.0      # market price cap, $/MWh


def load_data() -> pd.DataFrame:
    """Return 5-minute dispatch prices. REPLACE THIS with a real NEMweb pull.

    Expected columns: settlement (datetime), region (str), rrp (float).
    """
    rng = np.random.default_rng(7)
    periods = 12 * 24 * 90  # ~one quarter of 5-min intervals
    idx = pd.date_range("2026-01-01", periods=periods, freq="5min")

    frames = []
    for i, region in enumerate(REGIONS):
        base = 60 + 20 * np.sin(np.linspace(0, 90 * 2 * np.pi, periods))  # diurnal-ish
        noise = rng.normal(0, 15, periods)
        rrp = np.clip(base + noise, -100, None)

        # inject occasional spikes, more in QLD/SA to look NEM-realistic
        spike_rate = [0.004, 0.0025, 0.002, 0.0035, 0.0015][i]
        spike_mask = rng.random(periods) < spike_rate
        rrp[spike_mask] = rng.uniform(300, PRICE_CAP, spike_mask.sum())

        frames.append(pd.DataFrame({"settlement": idx, "region": region, "rrp": rrp}))

    return pd.concat(frames, ignore_index=True)


def build(out_path: str) -> None:
    df = load_data()
    df["is_spike"] = df["rrp"] >= SPIKE_THRESHOLD

    # --- summary stats per region ---
    summary = (
        df.groupby("region")
        .agg(
            intervals=("rrp", "size"),
            spikes=("is_spike", "sum"),
            max_rrp=("rrp", "max"),
            mean_rrp=("rrp", "mean"),
        )
        .reindex(REGIONS)
    )
    summary["spike_pct"] = 100 * summary["spikes"] / summary["intervals"]

    # spikes by hour of day, summed across regions
    df["hour"] = df["settlement"].dt.hour
    by_hour = df[df["is_spike"]].groupby("hour").size().reindex(range(24), fill_value=0)

    accent = "#E8743B"
    ink = "#14181B"
    muted = "#6B7280"

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Spike frequency by region (RRP &ge; ${SPIKE_THRESHOLD:,.0f}/MWh)",
            "When spikes happen (by hour of day)",
        ),
        column_widths=[0.5, 0.5],
    )

    fig.add_trace(
        go.Bar(
            x=summary.index,
            y=summary["spike_pct"],
            marker_color=accent,
            hovertemplate="%{x}<br>%{y:.3f}% of intervals<extra></extra>",
            name="Spike %",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=by_hour.index,
            y=by_hour.values,
            marker_color=ink,
            hovertemplate="%{x}:00<br>%{y} spikes<extra></extra>",
            name="Spikes",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        template="plotly_white",
        title=dict(
            text="<b>Spike Price Analysis</b> &nbsp;<span style='font-size:13px;color:#6B7280'>"
            "demonstration data &mdash; replace with NEMweb DispatchIS</span>",
            x=0.5,
            xanchor="center",
        ),
        font=dict(family="Inter, system-ui, sans-serif", color=ink, size=13),
        showlegend=False,
        margin=dict(t=90, l=60, r=40, b=60),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_yaxes(title_text="% of intervals", row=1, col=1, gridcolor="#EDEDE7")
    fig.update_yaxes(title_text="spike count", row=1, col=2, gridcolor="#EDEDE7")
    fig.update_xaxes(title_text="region", row=1, col=1)
    fig.update_xaxes(title_text="hour", row=1, col=2, dtick=3)

    fig.write_html(out_path, include_plotlyjs="cdn", full_html=True)
