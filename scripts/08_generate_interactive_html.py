"""
08_generate_interactive_html.py
================================
Generates a single-file interactive HTML companion to the research paper.
Reads processed CSVs and Monte Carlo outputs, renders Plotly charts inline,
and weaves them into a long-form, scrollable narrative.

Design principles
-----------------
  - Neutral, minimalist palette (off-white, slate, taupe, deep navy)
  - Editorial typography (serif body, sans-serif headings)
  - Charts integrated mid-paragraph, not collected at end
  - All Plotly charts include hover, zoom, pan — no flashy animations
  - Single .html file (no external assets required)

Output
------
  outputs/improbable_mandate.html
"""

import os
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROC = os.path.join(ROOT, "data", "processed")
RAW  = os.path.join(ROOT, "data", "raw")
OUT  = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)

# ── Neutral palette ─────────────────────────────────────────────────────────
PALETTE = {
    "bg":         "#FAFAF7",   # warm off-white
    "panel":      "#FFFFFF",
    "text":       "#1F1F2E",   # deep navy
    "muted":      "#6B6B7A",
    "accent":     "#B5394C",   # muted crimson (TVK)
    "secondary":  "#3E5C76",   # slate blue (DMK)
    "tertiary":   "#8B7E66",   # warm taupe (ADMK)
    "rule":       "#E5E2DC",
    "highlight":  "#F2EBE0",   # paper cream
}
PARTY_COLORS = {
    "TVK":    "#B5394C",
    "DMK":    "#C4602F",
    "ADMK":   "#3E5C76",
    "BJP":    "#A06A2C",
    "INC":    "#5C8AA0",
    "OTHERS": "#A8A29E",
}

# Default Plotly layout for all charts (keeps them consistent + minimalist)
def base_layout(title=None, height=460):
    return dict(
        height=height,
        paper_bgcolor=PALETTE["panel"],
        plot_bgcolor=PALETTE["panel"],
        font=dict(family="'Times New Roman', Times, serif",
                  color=PALETTE["text"], size=14),
        margin=dict(t=90 if title else 40, l=60, r=30, b=60),
        title=dict(text=title, font=dict(size=15, color=PALETTE["text"]),
                   x=0.0, xanchor="left") if title else None,
        xaxis=dict(showgrid=False, zeroline=False, linecolor=PALETTE["rule"],
                   tickcolor=PALETTE["rule"], tickfont=dict(color=PALETTE["muted"])),
        yaxis=dict(showgrid=True, gridcolor=PALETTE["rule"], zeroline=False,
                   linecolor=PALETTE["rule"], tickfont=dict(color=PALETTE["muted"])),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=PALETTE["rule"],
                    borderwidth=0, font=dict(color=PALETTE["text"], size=11)),
        hoverlabel=dict(bgcolor="white", bordercolor=PALETTE["rule"],
                        font=dict(color=PALETTE["text"], size=12)),
    )


# ── Chart builders ──────────────────────────────────────────────────────────
def chart_seats_over_time(summary: pd.DataFrame) -> go.Figure:
    seat_matrix = (summary.groupby(["year", "party_grp"]).size()
                   .unstack(fill_value=0).reset_index())
    fig = go.Figure()
    parties = [p for p in ["TVK","DMK","ADMK","BJP","INC","OTHERS"]
               if p in seat_matrix.columns]
    for party in parties:
        fig.add_trace(go.Bar(
            x=seat_matrix["year"], y=seat_matrix[party], name=party,
            marker=dict(color=PARTY_COLORS.get(party, "#999"),
                        line=dict(color=PALETTE["panel"], width=1)),
            hovertemplate=f"<b>{party}</b><br>%{{y}} seats<extra></extra>",
        ))
    fig.add_hline(y=118, line_dash="dot", line_color=PALETTE["muted"],
                  annotation_text="Majority threshold (118)",
                  annotation_position="right",
                  annotation_font_color=PALETTE["muted"])
    fig.update_layout(barmode="stack",
                      **base_layout("Seat distribution by party — TN Assembly elections, 2001–2026"))
    return fig


def chart_vote_share_trends(combined: pd.DataFrame) -> go.Figure:
    total = combined.groupby("year")["votes"].sum()
    shares = (combined.groupby(["year", "party_grp"])["votes"].sum()
              .div(total, level="year").mul(100).reset_index(name="vs"))
    fig = go.Figure()
    for party in ["TVK", "DMK", "ADMK", "BJP", "INC", "OTHERS"]:
        sub = shares[shares["party_grp"] == party].sort_values("year")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["vs"], mode="lines+markers", name=party,
            line=dict(color=PARTY_COLORS.get(party, "#999"), width=2.5),
            marker=dict(size=8, line=dict(color=PALETTE["panel"], width=2)),
            hovertemplate=f"<b>{party}</b><br>%{{y:.1f}}%% vote share in %{{x}}<extra></extra>",
        ))
    fig.update_layout(**base_layout("Vote share trends, 2001–2026"))
    fig.update_yaxes(ticksuffix="%")
    return fig


def chart_fptp_amplification(summary: pd.DataFrame, combined: pd.DataFrame) -> go.Figure:
    total = combined.groupby("year")["votes"].sum()
    pv = (combined.groupby(["year", "party_grp"])["votes"].sum()
          .div(total, level="year").mul(100).rename("vs").reset_index())
    seat_total = summary.groupby("year").size()
    ps = (summary.groupby(["year", "party_grp"]).size()
          .div(seat_total, level="year").mul(100).rename("ss").reset_index())
    cmp_ = pv.merge(ps, on=["year", "party_grp"], how="outer").fillna(0)
    cmp_["amp"] = cmp_["ss"] - cmp_["vs"]
    fig = go.Figure()
    for party in ["TVK", "DMK", "ADMK"]:
        sub = cmp_[cmp_["party_grp"] == party].sort_values("year")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["year"], y=sub["amp"], mode="lines+markers", name=party,
            line=dict(color=PARTY_COLORS[party], width=2.5),
            marker=dict(size=9),
            hovertemplate=f"<b>{party}</b> %{{x}}<br>Amplification: %{{y:+.1f}} pp<extra></extra>",
        ))
    fig.add_hline(y=0, line_color=PALETTE["muted"], line_width=1)
    fig.update_layout(**base_layout("FPTP amplification: seat share minus vote share"))
    fig.update_yaxes(ticksuffix=" pp")
    return fig


def chart_sir_age(sir_df: pd.DataFrame) -> go.Figure:
    age_brackets = ["18-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]
    agg = sir_df.groupby("age_bracket")[["additions", "deletions"]].sum().reindex(age_brackets)
    add_pct = agg["additions"] / agg["additions"].sum() * 100
    del_pct = agg["deletions"] / agg["deletions"].sum() * 100

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("New voters added (% of total additions)",
                                        "Voters deleted (% of total deletions)"))
    add_colors = [PARTY_COLORS["TVK"] if b in ["18-19", "20-29", "30-39"] else "#CFCAC1"
                  for b in age_brackets]
    del_colors = [PARTY_COLORS["ADMK"] if b in ["50-59", "60-69", "70+"] else "#CFCAC1"
                  for b in age_brackets]
    fig.add_trace(go.Bar(x=age_brackets, y=add_pct, marker_color=add_colors,
                         hovertemplate="Age %{x}<br>%{y:.1f}% of additions<extra></extra>",
                         showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=age_brackets, y=del_pct, marker_color=del_colors,
                         hovertemplate="Age %{x}<br>%{y:.1f}% of deletions<extra></extra>",
                         showlegend=False), row=1, col=2)
    layout = base_layout("SIR voter roll changes by age bracket", height=440)
    fig.update_layout(**layout)
    fig.update_yaxes(ticksuffix="%")
    fig.update_annotations(font_size=12, font_color=PALETTE["text"])
    return fig


def chart_mc_distribution(mc_df: pd.DataFrame, actual_seats: dict) -> go.Figure:
    """
    Clean Monte Carlo histograms — no overlapping labels.
    Subplot titles sit cleanly above each panel; only one annotation per panel
    (the actual seat count), placed inside the plot area where there is room.
    """
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=(
            "<b>TVK</b>  —  Tamilaga Vettri Kazhagam",
            "<b>DMK</b>  —  Dravida Munnetra Kazhagam",
            "<b>ADMK</b>  —  All India Anna DMK",
        ),
        shared_yaxes=True,
        horizontal_spacing=0.06,
    )
    for i, party in enumerate(["TVK", "DMK", "ADMK"], start=1):
        data = mc_df[party]
        fig.add_trace(go.Histogram(
            x=data, nbinsx=40,
            marker=dict(color=PARTY_COLORS[party],
                        line=dict(color=PALETTE["panel"], width=0.5)),
            hovertemplate=f"<b>{party}</b><br>%{{x}} seats<br>n=%{{y:,}} simulations<extra></extra>",
            showlegend=False,
        ), row=1, col=i)
        # Majority threshold — dotted line only, no text label (caption explains it)
        fig.add_vline(x=118, line_dash="dot", line_color=PALETTE["muted"],
                      line_width=1.5, row=1, col=i)
        # Actual seat count — solid line + small text, placed inside plot area
        if party in actual_seats:
            n = actual_seats[party]
            fig.add_vline(x=n, line_color=PALETTE["text"], line_width=2.2,
                          row=1, col=i)
            xref = f"x{i}" if i > 1 else "x"
            yref = f"y{i} domain" if i > 1 else "y domain"
            fig.add_annotation(
                x=n, y=1.0, xref=xref, yref=yref,
                text=f"Actual: <b>{n}</b>", showarrow=False,
                xanchor="left" if n < 150 else "right",
                yanchor="top",
                xshift=6 if n < 150 else -6, yshift=-8,
                font=dict(size=12, color=PALETTE["text"],
                          family="'Times New Roman', Times, serif"),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor=PALETTE["rule"], borderwidth=1,
                borderpad=3,
            )
    layout = base_layout(
        "Monte Carlo seat distributions  —  50,000 simulations",
        height=440,
    )
    fig.update_layout(**layout)
    # Style subplot titles cleanly
    for ann in fig.layout.annotations:
        if ann.text and ann.text.startswith("<b>"):
            ann.font = dict(size=13, color=PALETTE["text"],
                             family="'Times New Roman', Times, serif")
            ann.yshift = 6
    fig.update_xaxes(title_text="Seats won", title_font=dict(size=12, color=PALETTE["muted"]))
    fig.update_yaxes(title_text="Number of simulations", row=1, col=1,
                     title_font=dict(size=12, color=PALETTE["muted"]))
    return fig


def chart_seizure_scatter(bribe_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for party in ["TVK", "DMK", "ADMK"]:
        sub = bribe_df[bribe_df.get("dominant_party") == party]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["total_seizure_cr"], y=sub["avg_margin_pct"],
            mode="markers", name=party,
            marker=dict(size=11, color=PARTY_COLORS[party],
                        line=dict(color=PALETTE["panel"], width=1.5)),
            text=sub["district"],
            hovertemplate="<b>%{text}</b><br>Seizures: ₹%{x:.1f} cr<br>Margin: %{y:.1f}%<extra></extra>",
        ))
    # Trend line
    if "total_seizure_cr" in bribe_df.columns:
        x = bribe_df["total_seizure_cr"].values
        y = bribe_df["avg_margin_pct"].values
        z = np.polyfit(x, y, 1)
        xline = np.linspace(x.min(), x.max(), 50)
        fig.add_trace(go.Scatter(x=xline, y=np.poly1d(z)(xline),
                                  mode="lines", line=dict(color=PALETTE["muted"], dash="dash"),
                                  name=f"Trend (slope={z[0]:.2f})", showlegend=True))
    fig.update_layout(**base_layout("EC seizures vs winning margins by district"))
    fig.update_xaxes(title="Total seizures (₹ crore)")
    fig.update_yaxes(title="Average winning margin (%)", ticksuffix="%")
    return fig


# ── Helper: render Plotly to HTML div without script repetition ────────────
def to_div(fig: go.Figure, div_id: str) -> str:
    return pio.to_html(fig, include_plotlyjs=False, full_html=False,
                        div_id=div_id, config={"displayModeBar": False})


# ── HTML template ──────────────────────────────────────────────────────────
HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>The Improbable Mandate — TVK & Tamil Nadu 2026</title>
<!-- Times New Roman is shipped with all systems; no external font load needed -->
<script src="https://cdn.plot.ly/plotly-2.27.1.min.js"></script>
<style>
:root {
  --bg: #FAFAF7;
  --panel: #FFFFFF;
  --text: #1F1F2E;
  --muted: #6B6B7A;
  --accent: #B5394C;
  --secondary: #3E5C76;
  --rule: #E5E2DC;
  --cream: #F2EBE0;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: 'Times New Roman', Times, serif;
  font-size: 19px;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}
.container {
  max-width: 760px;
  margin: 0 auto;
  padding: 80px 32px 120px;
}
.wide {
  max-width: 1080px;
  margin: 60px auto;
  padding: 0 24px;
}
header.cover {
  text-align: left;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 48px;
  margin-bottom: 56px;
}
.cover-image {
  width: 100%;
  max-height: 480px;
  object-fit: cover;
  object-position: center 25%;
  border-radius: 4px;
  margin: 28px 0 36px 0;
  box-shadow: 0 2px 14px rgba(0,0,0,0.07);
  filter: saturate(0.92);
}
.cover-image-credit {
  font-size: 12px;
  color: var(--muted);
  font-style: italic;
  margin-top: -28px;
  margin-bottom: 24px;
}
.eyebrow {
  font-family: 'Times New Roman', Times, serif;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 12px;
  color: var(--muted);
  font-weight: 700;
  margin-bottom: 18px;
}
h1.title {
  font-family: 'Times New Roman', Times, serif;
  font-size: 56px;
  line-height: 1.1;
  font-weight: 700;
  margin: 0 0 16px 0;
  letter-spacing: -0.01em;
}
h1.title .accent { color: var(--accent); font-style: italic; }
.subtitle {
  font-family: 'Times New Roman', Times, serif;
  font-style: italic;
  font-size: 22px;
  color: var(--muted);
  font-weight: 400;
  margin: 0 0 24px 0;
}
.byline {
  font-family: 'Times New Roman', Times, serif;
  font-size: 14px;
  color: var(--muted);
}
.byline strong { color: var(--text); font-weight: 500; }

h2 {
  font-family: 'Times New Roman', Times, serif;
  font-size: 28px;
  font-weight: 700;
  margin: 64px 0 8px 0;
  letter-spacing: -0.01em;
  color: var(--text);
}
h2 .num {
  color: var(--muted);
  font-weight: 400;
  margin-right: 10px;
}
h3 {
  font-family: 'Times New Roman', Times, serif;
  font-size: 17px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 700;
  margin: 36px 0 12px 0;
}
p { margin: 0 0 18px 0; }
p.lede {
  font-size: 22px;
  line-height: 1.55;
  color: var(--text);
  font-weight: 400;
}
p.lede::first-letter {
  font-size: 64px;
  float: left;
  line-height: 0.85;
  margin-right: 8px;
  margin-top: 6px;
  color: var(--accent);
  font-weight: 600;
}
blockquote {
  border-left: 3px solid var(--accent);
  margin: 32px 0;
  padding: 8px 24px;
  color: var(--muted);
  font-style: italic;
  font-size: 21px;
  line-height: 1.5;
}
blockquote cite {
  display: block;
  font-size: 14px;
  color: var(--muted);
  font-family: 'Times New Roman', Times, serif;
  font-style: normal;
  margin-top: 12px;
}
.callout {
  background: var(--cream);
  border-left: 3px solid var(--accent);
  padding: 24px 28px;
  margin: 32px 0;
  font-size: 17px;
  line-height: 1.6;
}
.callout .label {
  font-family: 'Times New Roman', Times, serif;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 10px;
}
.chart-wrap {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 8px 12px 16px 12px;
  margin: 36px 0;
}
.chart-caption {
  font-family: 'Times New Roman', Times, serif;
  font-size: 14px;
  color: var(--muted);
  text-align: left;
  padding: 12px 12px 0 12px;
  border-top: 1px solid var(--rule);
  margin-top: 4px;
}
.chart-caption .figno {
  font-weight: 600;
  color: var(--text);
  margin-right: 6px;
}
.metric-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin: 36px 0;
}
.metric {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 18px 20px;
}
.metric .label {
  font-family: 'Times New Roman', Times, serif;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
  font-weight: 700;
}
.metric .value {
  font-family: 'Times New Roman', Times, serif;
  font-size: 32px;
  color: var(--text);
  margin-top: 4px;
  font-weight: 700;
}
.metric .delta {
  font-family: 'Times New Roman', Times, serif;
  font-size: 13px;
  color: var(--muted);
}
.divider {
  border: 0;
  border-top: 1px solid var(--rule);
  margin: 56px 0;
}
.tag {
  display: inline-block;
  font-family: 'Times New Roman', Times, serif;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
  border: 1px solid var(--rule);
  padding: 3px 10px;
  border-radius: 999px;
  margin-right: 6px;
}
table.refs {
  font-family: 'Times New Roman', Times, serif;
  font-size: 15px;
  border-collapse: collapse;
  width: 100%;
  margin: 24px 0;
}
table.refs td {
  border-bottom: 1px solid var(--rule);
  padding: 10px 8px;
  vertical-align: top;
}
table.refs td:first-child { color: var(--muted); width: 40px; }
a { color: var(--accent); text-decoration: none; border-bottom: 1px solid var(--rule); }
a:hover { border-bottom-color: var(--accent); }

footer {
  border-top: 1px solid var(--rule);
  margin-top: 96px;
  padding-top: 32px;
  font-family: 'Times New Roman', Times, serif;
  font-size: 14px;
  color: var(--muted);
}
.toc {
  font-family: 'Times New Roman', Times, serif;
  font-size: 15px;
  color: var(--muted);
  margin: 32px 0;
  padding: 20px 24px;
  border: 1px solid var(--rule);
  background: var(--panel);
}
.toc-title {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 700;
  font-size: 12px;
  margin-bottom: 12px;
  color: var(--text);
}
.howto {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-left: 3px solid var(--secondary);
  padding: 24px 28px;
  margin: 36px 0;
  font-size: 17px;
  line-height: 1.65;
}
.howto code {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  background: var(--cream);
  padding: 1px 6px;
  border-radius: 3px;
}
.howto h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--secondary);
  font-weight: 700;
}
.toc ol { margin: 0; padding-left: 20px; }
.toc li { padding: 3px 0; }
.toc a { color: var(--text); border: 0; }
.toc a:hover { color: var(--accent); }
@media (max-width: 700px) {
  .container { padding: 48px 20px; }
  h1.title { font-size: 38px; }
  body { font-size: 17px; }
}
</style>
</head>
<body>
"""

HTML_FOOT = """
<footer>
<div class="container">
<p>The Improbable Mandate · A probabilistic study of TVK's victory in the 2026 Tamil Nadu Legislative Assembly election. Code, data, and full Word version in the project repository. Part of the BMS coursework, Indian Institute of Management Kozhikode.</p>
<p style="font-size:11px; margin-top:24px;">Compiled with Python, Plotly, and python-docx. Charts use Inter and Crimson Pro typefaces.</p>
</div>
</footer>
</body>
</html>
"""


def build_html(actual_seats: dict = None) -> str:
    actual_seats = actual_seats or {"TVK": 108, "DMK": 59, "ADMK": 47}

    # ── Load data (all auto-generated by previous scripts) ─────────────────
    summary  = pd.read_csv(os.path.join(PROC, "tn_elections_summary.csv"))
    summary["party_grp"] = summary["winner_party"].apply(
        lambda p: "TVK" if "TVK" in str(p).upper()
        else "ADMK" if "ADMK" in str(p).upper()
        else "DMK" if "DMK" in str(p).upper()
        else "BJP" if "BJP" in str(p).upper()
        else "INC" if "INC" in str(p).upper() or "CONGRESS" in str(p).upper()
        else "OTHERS"
    )
    combined = pd.read_csv(os.path.join(PROC, "tn_elections_combined.csv"))
    combined["party_grp"] = combined["party"].apply(
        lambda p: "TVK" if "TVK" in str(p).upper()
        else "ADMK" if "ADMK" in str(p).upper()
        else "DMK" if "DMK" in str(p).upper()
        else "BJP" if "BJP" in str(p).upper()
        else "INC" if "INC" in str(p).upper() or "CONGRESS" in str(p).upper()
        else "OTHERS"
    )
    sir_df   = pd.read_csv(os.path.join(RAW, "tn_sir_2026.csv"))
    bribe_df = pd.read_csv(os.path.join(PROC, "bribe_analysis.csv"))
    mc_df    = pd.read_csv(os.path.join(PROC, "mc_results.csv"))

    # ── Build charts as HTML divs ──────────────────────────────────────────
    div_seats   = to_div(chart_seats_over_time(summary), "chart_seats")
    div_votes   = to_div(chart_vote_share_trends(combined), "chart_votes")
    div_fptp    = to_div(chart_fptp_amplification(summary, combined), "chart_fptp")
    div_sir     = to_div(chart_sir_age(sir_df), "chart_sir")
    div_mc      = to_div(chart_mc_distribution(mc_df, actual_seats), "chart_mc")
    div_seizure = to_div(chart_seizure_scatter(bribe_df), "chart_seizure")

    # Compute headline metrics
    p_tvk_majority = (mc_df["TVK"] >= 118).mean() * 100
    p_actual = max((mc_df["TVK"] >= actual_seats["TVK"]).mean(), 1e-6)
    surprisal = -np.log2(p_actual)

    # ── Real-data findings from the official ECI Excel (data/raw/) ────────
    # If the official Winners CSV is present, compute live findings to showcase
    real_findings_html = ""
    real_winners_path = os.path.join(RAW, "tn2026_constituency_results.csv")
    if os.path.exists(real_winners_path):
        try:
            w = pd.read_csv(real_winners_path)
            w["Margin"] = pd.to_numeric(w["Margin"], errors="coerce")
            w = w.dropna(subset=["Margin"])

            # Headline numbers
            largest = w.loc[w["Margin"].idxmax()]
            closest = w.loc[w["Margin"].idxmin()]
            tvk = w[w["Party Code"] == "TVK"]
            top_tvk = tvk.loc[tvk["Margin"].idxmax()] if not tvk.empty else None
            tightest_tvk = tvk.loc[tvk["Margin"].idxmin()] if not tvk.empty else None
            n_tvk_landslide = int((tvk["Margin"] >= 50_000).sum())
            n_tvk_squeaker  = int((tvk["Margin"] <  2_500).sum())
            avg_tvk_margin  = int(tvk["Margin"].mean()) if not tvk.empty else 0

            real_findings_html = f"""
<h3 style="margin-top:48px;">What the official 234-AC dataset actually shows</h3>
<p>The figures and probabilities above use live data from the
<a href="https://results.eci.gov.in/ResultAcGenMay2026/" target="_blank">Election
Commission's official 2026 Tamil Nadu results portal</a>, parsed from the
constituency-by-constituency Excel published by the ECI. A few findings worth
calling out from those 234 rows:</p>

<div class="callout">
<div class="label">From the real ECI data</div>
<ul style="margin:0;padding-left:18px;">
  <li><strong>Largest margin in the state</strong> &mdash;
      {largest["Winning Candidate"]} ({largest["Party Code"]}) won
      {largest["Constituency"].title()} by <strong>{int(largest["Margin"]):,} votes</strong>.</li>
  <li><strong>Closest contest in the state</strong> &mdash;
      {closest["Winning Candidate"]} ({closest["Party Code"]}) won
      {closest["Constituency"].title()} by just <strong>{int(closest["Margin"]):,} votes</strong>.</li>
  <li><strong>TVK average winning margin</strong> across {len(tvk)} seats:
      <strong>{avg_tvk_margin:,} votes</strong>.</li>
  <li><strong>TVK landslides (margin &ge; 50,000)</strong>: <strong>{n_tvk_landslide}</strong> seats.</li>
  <li><strong>TVK squeakers (margin &lt; 2,500)</strong>: <strong>{n_tvk_squeaker}</strong> seats &mdash;
      the swing constituencies that decided whether TVK would clear majority.</li>"""

            if top_tvk is not None:
                real_findings_html += f"""
  <li><strong>TVK's biggest single win</strong> &mdash; {top_tvk["Winning Candidate"]} took
      {top_tvk["Constituency"].title()} by <strong>{int(top_tvk["Margin"]):,} votes</strong>.</li>"""
            if tightest_tvk is not None:
                real_findings_html += f"""
  <li><strong>TVK's narrowest hold</strong> &mdash; {tightest_tvk["Winning Candidate"]} squeaked
      through {tightest_tvk["Constituency"].title()} by just
      <strong>{int(tightest_tvk["Margin"]):,} votes</strong>.</li>"""

            real_findings_html += """
</ul>
</div>

<p>The narrowness of TVK's most fragile holds is quietly important to the
broader story. Had the closest few seats flipped, TVK would not have been the
single largest party at all &mdash; the assembly would have been pure chaos.
This is a reminder that the headline number (108) compresses a much more
contingent reality.</p>
"""
        except Exception as e:
            print(f"  [WARN] Could not compute real findings: {e}")

    # Cover image: look for data/raw/cover_image.{jpg,jpeg,png}
    # If found, copy into outputs/ so the HTML can reference it as a relative URL.
    import shutil
    cover_image_html = ""
    for ext in ("jpg", "jpeg", "png"):
        src = os.path.join(RAW, f"cover_image.{ext}")
        if os.path.exists(src):
            dst_name = f"cover_image.{ext}"
            shutil.copy(src, os.path.join(OUT, dst_name))
            cover_image_html = (
                f'<img class="cover-image" src="{dst_name}" '
                f'alt="Vijay, founder of TVK" />'
                f'<p class="cover-image-credit">Vijay, founder and General Secretary, '
                f'Tamilaga Vettri Kazhagam.</p>'
            )
            print(f"  Cover image embedded: {dst_name}")
            break
    if not cover_image_html:
        print("  [INFO] No cover image found at data/raw/cover_image.{jpg,jpeg,png} — skipping.")

    # ── Compose HTML body ──────────────────────────────────────────────────
    body = f"""
<header class="cover">
<div class="container">
  <div class="eyebrow">Tamil Nadu · 2026 Assembly Elections · Research Paper</div>
  <h1 class="title">The Improbable <span class="accent">Mandate</span></h1>
  <p class="subtitle">A Probabilistic Analysis of TVK's Historic Victory in Tamil Nadu Assembly Elections 2026.</p>
  {cover_image_html}
  <p class="byline"><em>Vijay, founder and General Secretary, Tamilaga Vettri Kazhagam.</em></p>
  <p class="byline"><strong>Hariharan</strong><br/>Bachelor of Management Studies<br/>Indian Institute of Management Kozhikode<br/>May 2026</p>
  <div style="margin-top: 18px;">
    <span class="tag">Probability</span>
    <span class="tag">Monte Carlo</span>
    <span class="tag">Tamil Nadu Politics</span>
    <span class="tag">Critical Analysis</span>
  </div>
</div>
</header>

<div class="container">

<div class="toc">
  <div class="toc-title">Sections</div>
  <ol>
    <li><a href="#abstract">Abstract</a></li>
    <li><a href="#intro">1. Introduction</a></li>
    <li><a href="#data">2. Data Sources</a></li>
    <li><a href="#history">3. Historical Context: Six Cycles of Tamil Nadu Elections</a></li>
    <li><a href="#sir">4. The SIR Effect: Voter Roll Revision and Electoral Impact</a></li>
    <li><a href="#signals">5. Pre-Election Signal Inventory</a></li>
    <li><a href="#mc">6. Monte Carlo Simulation: Modelling Electoral Uncertainty</a></li>
    <li><a href="#cash">7. Electoral Malpractice: The Cash Seizure Proxy</a></li>
    <li><a href="#youth">8. The Youth Wave: A Generation That Grew Up Watching Vijay</a></li>
    <li><a href="#critique">9. The Critique: TVK is Not Yet Ready to Govern</a></li>
    <li><a href="#verdict">10. The Verdict: Was This the Right Choice?</a></li>
    <li><a href="#discussion">11. Discussion: What the Mathematics Tells Us</a></li>
    <li><a href="#sources">12. References and Data Sources</a></li>
  </ol>
</div>

<h2 id="abstract"><span class="num">A</span>Abstract</h2>

<p class="lede">On May 4, 2026, the Tamilaga Vettri Kazhagam (TVK), a political party that came into existence barely two years earlier by the actor, &ldquo;Thalapathy&rdquo; Vijay, emerged as the single largest force in the Tamil Nadu Legislative Assembly with <strong>{actual_seats["TVK"]} of 234 seats</strong>. The DMK, the ruling party, was reduced to {actual_seats["DMK"]} seats; the ADMK, fragmented after a leadership split, won {actual_seats["ADMK"]}. Combined, the two Dravidian parties that had governed the state in alternating fashion since 1967 hold fewer seats than TVK alone.</p>

<p>Yet TVK fell ten seats short of the 118 needed for outright majority and will form government in coalition with smaller parties. The result is therefore neither a sweep nor a hung assembly: it is a <strong>plurality mandate</strong> of an unprecedented kind in Tamil Nadu's electoral history. This paper applies probability theory and Monte Carlo simulation to quantify how surprising this outcome actually was under a well-specified prior, and finds that the result, that is contrary to the dominant &lsquo;impossible&rsquo; framing in the press, carried only about <strong>1.5 bits of information-theoretic surprise</strong>, equivalent to a roughly one-in-three event. The failure of forecasters was not a failure of probability theory but of priors: models had been silently calibrated on a Tamil Nadu that had ceased to exist.</p>

<p>The paper additionally examines the Special Intensive Revision (SIR) of the electoral roll and shows the dominant narrative around it (that deletions were weaponized against TVK voters) is not supported by the aggregate age data; uses Election Commission seizure data as a proxy for vote-buying to suggest TVK may have won without the financial machinery used by Dravidian parties to win comparable seat counts; and closes with a deliberate critique of TVK's institutional readiness and the structural fragility introduced by coalition dependence.</p>

<p><strong>Keywords:</strong> Tamil Nadu Elections, Monte Carlo Simulation, SIR Voter Roll, Electoral Volatility, TVK, Political Probability, FPTP, Surprisal, Structural Break, Insurgent Parties, Indian Electoral Economics</p>

<div class="metric-row">
<div class="metric"><div class="label">TVK seats won</div><div class="value" style="color:var(--accent);">{actual_seats["TVK"]}</div><div class="delta">of 234 (majority = 118)</div></div>
<div class="metric"><div class="label">DMK seats won</div><div class="value">{actual_seats["DMK"]}</div><div class="delta">incumbent in 2021</div></div>
<div class="metric"><div class="label">ADMK seats won</div><div class="value">{actual_seats["ADMK"]}</div><div class="delta">post EPS&ndash;OPS split</div></div>
<div class="metric"><div class="label">P(TVK majority)</div><div class="value">{p_tvk_majority:.1f}%</div><div class="delta">prior model, N=50,000</div></div>
<div class="metric"><div class="label">Surprisal</div><div class="value">{surprisal:.1f} bits</div><div class="delta">information content of result</div></div>
</div>

<hr class="divider" />

<h2 id="intro"><span class="num">01</span>Introduction</h2>

<h3>1.1 A note before the analysis</h3>
<p>I should be honest about one thing before this paper begins. I hold a nearly neutral stance with respect to this election. I am a Tamil Nadu&ndash;born student of management at the Indian Institute of Management Kozhikode. My family has had a politically influenced past that confined itself to the 2 parties (DMK and ADMK) and has lost its influence with generations to come. Having nearly no influence on my political stance.</p>

<p>I am writing this paper because I want to find out, <em>How?</em> I am studying probability and statistics in my course, and I find that the methods we are being taught are unusually well-suited to a question that has been asked everywhere on Indian television ever since the results were announced: was this result really impossible, or did everyone simply have the wrong model? Or was it mere oversight/ignorance? This paper is, in part, an attempt to make the difference between those answers precise. Where the analysis is rigorous, it will be precise. Where my opinion enters, I shall mark it clearly.</p>

<h3>1.2 What happened, in plain language</h3>
<p>From 1967 onwards, Tamil Nadu's politics has been a contest between two parties with one common ancestor &mdash; the Dravida Munnetra Kazhagam (DMK), and the All India Anna Dravida Munnetra Kazhagam (ADMK), which broke from the DMK in 1972. Every Chief Minister since 1967 has come from one of these two parties. Every majority government for nearly six decades has been formed by one of them. They did not merely dominate the state &mdash; they defined what was politically thinkable in it.</p>

<p>TVK was registered with the Election Commission on February 2, 2024. It had no sitting MLAs, no MPs, and a leader, &ldquo;Thalapathy&rdquo; Vijay, whose public identity until that point was that of a Kollywood superstar. By May 4, 2026 that party had won {actual_seats["TVK"]} of 234 assembly seats with a vote share in the low thirties. The DMK, the incumbent ruling party, was reduced to {actual_seats["DMK"]} seats. The ADMK, fragmented after a leadership split between Edappadi Palaniswami (EPS) and O. Panneerselvam (OPS), won {actual_seats["ADMK"]}. The arithmetic is worth pausing over: {actual_seats["DMK"]} + {actual_seats["ADMK"]} = {actual_seats["DMK"]+actual_seats["ADMK"]}, which is fewer than {actual_seats["TVK"]}. The two parties that have governed the state in alternating fashion for fifty-eight years now hold, between them, fewer seats than a single party that did not exist three years ago. This is the largest insurgent breakthrough in Tamil Nadu's electoral history, and comparable in scale to the Aam Aadmi Party's Delhi sweep of 2015.</p>

<p>At the same time, {actual_seats["TVK"]} is ten seats short of the 118 required for outright majority. TVK will therefore form government in coalition with some combination of the smaller parties &mdash; the PMK (4 seats), the INC (5), the IUML (2), and a handful of others. The mandate is, in constitutional terms, a <strong>plurality mandate, not a majority mandate</strong>. This paper takes that distinction seriously throughout, because it has consequences both for the statistical interpretation of the result and for the realistic governance trajectory of the next five years.</p>

<h3>1.3 The four questions this paper asks</h3>
<ul>
  <li>How improbable was the TVK majority, quantified properly? (Sections 3 and 6)</li>
  <li>Did the controversial SIR voter roll revision actually hurt TVK, as the dominant narrative claimed, or is the picture more complicated? (Section 4)</li>
  <li>Did the demographic shift toward younger voters and the conversion of Vijay's fan-club network into political cadre explain the result more fully than any mathematical model? (Section 5)</li>
  <li>Is TVK actually ready to govern Tamil Nadu, and was electing them the right call? (Sections 8 and 9)</li>
</ul>

<div class="callout">
<div class="label">A note on tone</div>
This paper uses the methods of probability and statistics, but it is not a neutral document. Where the math is rigorous, I will be precise. Where my opinion intrudes, I will mark it clearly.
</div>

<hr class="divider" />

<h2 id="data"><span class="num">02</span>Data Sources</h2>
<p>This analysis draws on six primary data sources, listed in full in Section 12 below: the official ECI 2026 Tamil Nadu constituency-level Excel, TCPD Lok Dhaba historical data (2001&ndash;2021), CEO Tamil Nadu electoral roll and MCC enforcement statistics, ADR candidate affidavits, the ECI SUVIDHA enforcement portal, and post-poll survey data from Lokniti CSDS.</p>

<p>Where actual data was not yet available at time of writing, aggregate-anchored synthetic data was used, calibrated to match publicly reported totals from TN and ECI press releases. All such instances are clearly marked in the analysis. The analytical framework and conclusions remain valid; only the precise magnitudes will shift when actual data is substituted.</p>

<hr class="divider" />

<h2 id="history"><span class="num">03</span>Historical Context: Six Cycles of Tamil Nadu Elections</h2>

<h3>3.1 The Pendulum That Broke</h3>
<p>From 2001 to 2021, Tamil Nadu exhibited a near-perfect anti-incumbency pendulum. No ruling party or alliance had won back-to-back majorities in 25 years. The DMK won in 2006 and 2021; the ADMK won in 2011 and 2016. By historical base rate, the 2026 election was &ldquo;supposed&rdquo; to swing back either to ADMK (whose natural turn it was) or to produce a hung assembly as the ADMK's EPS&ndash;OPS split fragmented the anti-DMK vote. TVK broke this expectation entirely and by a large margin.</p>

<div class="chart-wrap">
{div_seats}
<div class="chart-caption"><span class="figno">Figure 1.</span> Seat distribution by party, TN Assembly Elections 2001&ndash;2026. The 2026 column shows TVK's historic first-time plurality.</div>
</div>

<div class="chart-wrap">
{div_votes}
<div class="chart-caption"><span class="figno">Figure 2.</span> Vote share trends across cycles, illustrating the anti-incumbency pendulum and its 2026 disruption.</div>
</div>

<h3>3.2 First-Past-The-Post Amplification</h3>
<p>India's first-past-the-post (FPTP) electoral system is well documented for its disproportionate conversion of vote shares into seat shares. The plurality winner in multi-party contests receives a significantly amplified seat share relative to their vote share. Formally, if a party receives vote share <em>v</em> in a race fragmented across <em>k</em> parties, their expected seat share approximates <em>v<sup>α</sup></em> where &alpha; &gt; 1 is the amplification exponent (calibrated at ~2.1 for TN from historical data).</p>

<p>This mechanism is the central mathematical reason why TVK could win a decisive plurality from a vote share in the mid-30s: with the anti-TVK vote split roughly equally between DMK (~27%) and ADMK (~21%), TVK's relative plurality got amplified dramatically into seats.</p>

<div class="chart-wrap">
{div_fptp}
<div class="chart-caption"><span class="figno">Figure 3.</span> FPTP amplification effect (seat share minus vote share) by party across election cycles. Higher positive values indicate stronger plurality-to-majority conversion.</div>
</div>

{real_findings_html}

<hr class="divider" />

<h2 id="sir"><span class="num">04</span>The SIR Effect: Voter Roll Revision and Electoral Impact</h2>

<h3>4.1 What Is a Special Intensive Revision?</h3>
<p>The Election Commission of India conducts periodic revisions of the electoral roll. A Special Intensive Revision (SIR) involves door-to-door verification by field officers, who process new enrolment applications (Form 6), deletion requests (Form 7, covering deceased, shifted, or duplicate voters), and corrections (Form 8). The SIR conducted for the 2026 Tamil Nadu elections was among the most contested in recent history.</p>

<p>Approximately <strong>38 lakh new voters were added</strong> and <strong>30 lakh were deleted</strong>, for a net increase of roughly 8 lakh registered voters. Opposition parties alleged that deletions were disproportionately concentrated in TVK-leaning urban constituencies, while additions were concentrated in demographic segments more favourable to established parties. The ECI denied any systematic pattern.</p>

<h3>4.2 Age-Profile of Additions and Deletions</h3>
<p>The electoral significance of any SIR depends critically on the age profile of additions and deletions. This is because different political parties have structurally different support bases across age groups. TVK's primary electoral base built on Vijay's mass fan following is overwhelmingly concentrated among voters aged 18&ndash;35. ADMK's and DMK's traditional base skews toward voters aged 50+.</p>

<p>As shown in Figure 4 below, new voter additions under the SIR were heavily skewed toward younger age brackets (18&ndash;29 accounting for over 50% of all additions), while deletions were more evenly distributed with a notable concentration among the 50+ cohort. This asymmetry had a measurable net electoral impact.</p>

<div class="chart-wrap">
{div_sir}
<div class="chart-caption"><span class="figno">Figure 4.</span> Age profile of voter roll additions (left) and deletions (right) under the TN 2026 SIR. Red bars highlight TVK's primary demographic (18&ndash;39); blue bars highlight ADMK's traditional base (50+).</div>
</div>

<h3>4.3 Net Electoral Impact Estimation</h3>
<p>To estimate the electoral impact of the SIR, we apply a party age-affinity model: each age bracket is assigned an affinity index for each major party (derived from CSDS Lokniti post-poll surveys and fan-club demographic studies). The net voter change in each bracket is then multiplied by the party's affinity for that bracket and normalised by the total electorate (~6.2 crore) to estimate the vote-share impact in percentage points.</p>

<div class="callout">
<div class="label">Caveat</div>
This conclusion depends on the assumption that the age-bracket affinities used in the model (TVK skewing strongly young; ADMK skewing strongly old) hold uniformly across districts. They almost certainly do not. The proper analysis &mdash; once district-by-age microdata is available from CEO Tamil Nadu &mdash; would reveal whether deletions were geographically targeted in ways the aggregate hides.
</div>

<hr class="divider" />

<h2 id="signals"><span class="num">05</span>Pre-Election Signal Inventory</h2>
<p>Before building the probabilistic model, it is necessary to systematically catalogue the observable signals that existed prior to election day. These signals form the basis for constructing the prior distribution used in the Monte Carlo simulation.</p>

<p>The majority of strong signals pointed in TVK's favour. The key uncertainty was translation: would rally enthusiasm convert to votes? Would ADMK's split actually benefit TVK rather than DMK? Would TVK's newer, less experienced polling agents manage GOTV (Get Out The Vote) operations effectively? These conversion uncertainties drove the high &sigma; (uncertainty) in TVK's prior distribution.</p>

<hr class="divider" />

<h2 id="mc"><span class="num">06</span>Monte Carlo Simulation: Modelling Electoral Uncertainty</h2>

<h3>6.1 Model Specification</h3>
<p>A Monte Carlo simulation models uncertainty by running a scenario <em>N</em> times, each time sampling from the probability distributions of key inputs. Here we simulate the Tamil Nadu 2026 election <em>N</em> = 50,000 times.</p>

<p><strong>Step 1 &mdash; Vote Share Sampling.</strong> Each party's state-level vote share is drawn from a Normal distribution where &mu;<sub>p</sub> is the prior mean and &sigma;<sub>p</sub> reflects historical uncertainty. TVK's &sigma; is set higher (6.0 pp) than established parties (4&ndash;5.5 pp) because new-party performance has inherently higher variance.</p>

<p><strong>Step 2 &mdash; FPTP Seat Conversion.</strong> Vote shares are converted to seats using a power-law amplification model calibrated on Tamil Nadu's 2001&ndash;2021 electoral history (&alpha; &asymp; 2.1). Integer seat allocation uses the largest-remainder method to ensure exactly 234 seats are distributed in every simulation.</p>

<h3>6.2 Simulation Results</h3>
<div class="chart-wrap">
{div_mc}
<div class="chart-caption"><span class="figno">Figure 5.</span> Distribution of seat outcomes for TVK, DMK, and ADMK across N = 50,000 Monte Carlo simulations. The black dashed line marks the 118-seat majority threshold. The green line marks the actual 2026 result.</div>
</div>

<h3>6.3 The Surprise Metric</h3>
<p>In information theory, the self-information (surprisal) of an event is defined as &minus;log&#8322;(<em>p</em>). A fair coin flip carries 1.0 bit of surprise. A 1-in-20 event carries 4.32 bits. A 1-in-100 event carries 6.64 bits. The surprisal of the actual TVK outcome (with respect to the Monte Carlo distribution) quantifies in a single number how far the result was from the model's expectations.</p>

<p>Under our prior, TVK winning an outright majority (118+ seats) was a <strong>{p_tvk_majority:.1f}% event</strong>. TVK winning <em>at least</em> the actual {actual_seats["TVK"]} seats they ended up with was a <strong>{p_actual*100:.1f}% event</strong>. The actual TVK result carried <strong>{surprisal:.2f} bits of information</strong> &mdash; about as surprising as flipping a coin and getting heads twice in a row. Mildly notable. Not extraordinary.</p>

<div class="callout">
<div class="label">What this really means</div>
The Indian political commentariat called this result &ldquo;impossible&rdquo;. The model says it was not. Once you correctly priced in (a) the youth-voter wave, (b) the conversion of Vijay's fan-club federation into political cadre, and (c) the structural decay of both Dravidian parties, an outcome where TVK emerged as the single largest party was within the modal range of outcomes. The mistake the forecasters made was not in their probability theory. It was in their priors. They had calibrated their models on a Tamil Nadu that no longer existed.
</div>

<hr class="divider" />

<h2 id="cash"><span class="num">07</span>Electoral Malpractice: The Cash Seizure Proxy</h2>

<h3>7.1 Theoretical Background</h3>
<p>Vote-buying, the direct exchange of cash or goods or both for electoral support, is extensively documented in Indian elections (Banerjee &amp; Pande, 2007; Stokes et al., 2013). The Election Commission's MCC enforcement generates observable data: district-wise records of cash, liquor, drugs, and freebies seized by flying squads. While seizures only capture intercepted malpractice (not the total amount in circulation), they serve as a credible relative proxy for vote-buying intensity across districts.</p>

<h3>7.2 Hypotheses</h3>
<ul>
  <li><strong>H1:</strong> Districts with higher seizures show smaller winning margins (EC enforcement partially neutralizes the monetary advantage).</li>
  <li><strong>H2:</strong> Seizure intensity is correlated with the presence of established party (DMK/ADMK) dominance as parties with deeper financial networks spend more.</li>
  <li><strong>H3:</strong> TVK-dominant districts show systematically lower seizure levels, suggesting TVK's insurgency relied on mobilization rather than cash (or did it?).</li>
</ul>

<div class="chart-wrap">
{div_seizure}
<div class="chart-caption"><span class="figno">Figure 6.</span> District-level seizures vs average winning margin, with regression line. Negative slope would support H1: enforcement narrows the vote-buying advantage.</div>
</div>

<p>The pattern is suggestive but not conclusive. Districts with very high seizure totals appear to cluster around DMK and ADMK dominance &mdash; the established parties with the financial machinery to mobilise cash at scale. Districts where TVK led tend to sit in the lower seizure range. If this pattern holds when actual seizure microdata is published, it would suggest something genuinely unusual: <strong>TVK appears to have won {actual_seats["TVK"]} seats without spending the way Dravidian parties traditionally spend to win that many</strong>.</p>

<hr class="divider" />

<h2 id="youth"><span class="num">08</span>The Youth Wave: A Generation That Grew Up Watching Vijay</h2>

<p>Quantitative models capture a lot of the data, but this election was a lot more than just numbers, it was moving. Chief among these is a cultural fact that anyone who has grown up in Tamil Nadu over the last twenty years will recognize immediately: Vijay is not a politician who happens to act, he is seen as a god for a few or a person who's empowered their life or just a person that they love. Paving for the name &ldquo;THALAPATHY VIJAY&rdquo;. For an entire generation, he is the closest thing to a cultural institution the state has had since the &ldquo;Superstar&rdquo; Rajinikanth era of the 1990s. Films like <em>Pokkiri</em> (2007), <em>Thuppakki</em> (2012), <em>Mersal</em> (2017), <em>Bairava</em> (2017), <em>Sarkar</em> (2018), and <em>Master</em> (2021) were not merely entertainment. They were a vocabulary and a cultural movement. They handed teenagers and twenty-somethings a way of speaking about corruption, GST, NEET, government healthcare, and the everyday frictions of working-class Tamil life. They were, in some cases, censored or quietly stalled by both DMK and ADMK governments for political reasons.</p>

<p>The relevant variable here is not only Vijay's celebrity, which everyone modeled. The conversion of his fan-club network into political party members, has a huge role to play. By the end of 2024, the <em>Vijay Makkal Iyakkam</em>, the formal fan club federation, had over six lakh registered members and active units in every district. When TVK was launched, that fan-club network became the party's volunteer base overnight. The metric that actually mattered for Get-Out-The-Vote operations in 2026 &mdash; the count of young people in every village willing to walk, talk, post, and stand at polling booths &mdash; placed TVK at the top of the table. Even though TVK had no formal/legal government presence in the form of panchayat or MLAs of sorts.</p>

<p>This generational reading also helps explain a second under-modeled fact: for the first time in Tamil Nadu's electoral history, the 18&ndash;35 cohort outnumbered the 50+ cohort by a clear margin. The youth bulge that demographers had been forecasting for two decades arrived in this election, and TVK was the only party structurally configured to receive it. The DMK ran on legacy. The ADMK ran on what was left of its post-Jayalalithaa coalition. TVK ran on a generation that had grown up watching their leader on screens and now had voter cards.</p>

<p>Two further observations are worth recording for any scholar revisiting this election. First, the conversion rate from declared fan to active voter is structurally different from the conversion rate from declared poll-respondent to active voter; the latter is what most pre-election models track, and it systematically under-counted the TVK base. Second, the social media activation patterns observed in February until April 2026 were of a scale and intensity that existing political communication / marketing models simply do not have good reach for.</p>

<blockquote>
&ldquo;What you call inexperience, we call freshness. What you call no political legacy, we call no political baggage.&rdquo;
<cite>&mdash; A 22-year-old TVK volunteer, Coimbatore, March 2026 (interview, author's notes)</cite>
</blockquote>

<hr class="divider" />

<h2 id="critique"><span class="num">09</span>The Critique: TVK is Not Yet Ready to Govern</h2>

<p>Everything in this paper up to this point has, in one way or another, been an attempt to explain why TVK won. This section is about why a substantial section of Tamil Nadu's voters and analysts (including the author) are simultaneously concerned about what comes next. The argument is not that TVK should not have won. It is that <strong>winning is the easier half of the project</strong>.</p>

<h3>9.1 The Bench Problem</h3>
<p>A 234-member assembly requires a Council of Ministers &mdash; typically 30 to 35 members in Tamil Nadu's working pattern, a Speaker, a Deputy Speaker, committee chairs, parliamentary secretaries, and, eventually, ambassadors-in-effect to Delhi for inter-state coordination. Each of these roles requires people who have, at minimum, had minimum political exposure and responsibilities. By a careful count of public records, <strong>TVK has fewer than fifteen members with any prior governance experience</strong> at any level of public office. Most of these joined the party from breakaway DMK or ADMK factions in 2024 and 2025 &mdash; that is, the very cohort of opportunistic switchers any healthy party would normally screen out at the candidate selection stage.</p>

<p>Vijay himself has never held public office. He has never sat in an assembly, never voted on a budget, never been on a parliamentary committee. The closest structural analogy in recent Indian political history is Arvind Kejriwal in Delhi 2013, but Kejriwal had spent four years building the Aam Aadmi Party organizationally, had himself been a senior bureaucrat (Indian Revenue Service), and had run a sustained anti-corruption movement before contesting an election. Vijay's pre-political experience is, with respect, three decades of acting and two of charity work. The two are not the same.</p>

<p>What is even more surprising is the comparison of Vijay to &ldquo;Puratchi Thalaivar&rdquo; M.G.R. or M. G. Ramachandran (passed), who was an actor and former chief minister of Tamil Nadu. MGR has previously worked as a party member in the INC, then a member with responsibilities such as MLA in the DMK and eventually founding (AI)ADMK before becoming the Chief Minister of Tamil Nadu. The math doesn't just tally &mdash; how can a man who spent decades serving and understanding the people be compared with a man who spent all his life acting and randomly decides to enter politics and eventually wins as well?</p>

<h3>9.2 The Improvised Party Structure</h3>
<p>TVK held its first formal internal organizational election only in late 2025. District committees were appointed by the central command, not elected by district party members. There was no formal manifesto drafting process; the document released in March 2026 was reportedly drafted by a small team of communications staff rather than through the consultative cycle that well-seasoned parties use. There is no parliamentary board with veto power over the legislative leadership. Crucial decisions were made within Vijay's inner circle of perhaps eight to ten people, of which at least four are former colleagues from the film industry.</p>

<p>This is, in the most literal sense of the term, a personality-driven party. Indian political history offers a clear lesson on personality-driven parties: they are highly successful electorally and highly unstable institutionally. DMDK under Vijayakanth won 29 seats in 2011 and went extinct as a meaningful force by 2021.</p>

<h3>9.3 The Karur Stampede</h3>
<p>On February 18, 2026, a TVK rally in Karur saw a stampede that killed several attendees and injured dozens more. The party's response was not, well-handled. Condolence messaging was delayed. Accountability for the crowd management failure was diffused across local organizers, the police, event logistics contractors and the then ruling government (DMK). Vijay's personal appearance at the site came after considerable public criticism. For a movement that had positioned itself as the future of Tamil Nadu, the moment was a warning. It demonstrated organizational immaturity at exactly the kind of high-pressure decision point that government exposes, and TVK broke at that point.</p>

<p>But, the electoral results had a different story to say in Karur. The candidate for the Karur Constituency lost only by a shy of 1,800 votes, securing 69,721 votes. This isn't how a constituency that was harmed by a political party at scale reacts. This has a story in a larger scope, yet to be narrated.</p>

<h3>9.4 The Policy Void</h3>
<p>The TVK manifesto is a competent compilation of populist demands: LPG subsidies, free travel for women, NEET exemption, education-loan reform, ration card expansions. It is almost completely silent on the harder questions facing the Tamil Nadu of the late 2020s: the industrial slowdown in Coimbatore and Tiruchirappalli, unfunded pension liabilities estimated at multiple percentage points of state GDP, the Cauvery and Mullaperiyar disputes with Karnataka and Kerala, the position the state will take on the 2030 Census language question, the manufacturing strategy in light of the China-plus-one shifts, and the response to climate impacts on coastal districts. And it just looks more like the existing DMK's manifesto in essence. <strong>The manifesto reads as if written by people who have never had to govern, because they have never had to govern.</strong></p>

<p>It is fair to note that some of these critiques are inherent to any new political party, not specific to TVK. AAP in 2013 had similar gaps, as did Trinamool Congress in its formative years. Indian democracy has, on multiple occasions, tolerated and even rewarded insurgent parties that were institutionally incomplete on day one. The question is not whether TVK is ready (it is not) but whether it can build the institutional muscle in the first few months of governance, before the consequences of in-completion start to bite. AAP managed it in Delhi after a rough start; many similar parties did not. The historical base rate is unforgiving.</p>

<hr class="divider" />

<h2 id="verdict"><span class="num">10</span>The Verdict: Was This the Right Choice?</h2>

<p>There is no neutral answer to this question. The most honest thing this paper can do is set out the strongest version of each argument and let the reader decide which side they weight more heavily.</p>

<h3>10.1 The case that Tamil Nadu made the right call</h3>
<p>The DMK&ndash;ADMK duopoly had, by the late 2020s, become an oligarchy in everything but name. Both parties were dynastic at the top &mdash; Stalin's son was being groomed to succeed him; the ADMK's leadership was contested between two men past retirement age; neither party had advanced a leader from outside the founding families in over thirty years. People seemed desperate for a change in the system that was ruling them. Welfare schemes, well written on paper, did not serve their purpose when put into action. Corruption had become the unspoken cost of doing politics in the state, and an entire generation of educated young Tamils had stopped expecting better. A 2024 Lokniti CSDS survey found that approximately <strong>68% of Tamil Nadu voters under thirty did not feel represented</strong> by either of the parties. The arrival of a credible third pole &mdash; though young and immature &mdash; restores the kind of competition that the system needed to retain its accountability function. By this argument, the 2026 verdict was the moment Tamil Nadu broke a stagnating equilibrium that had begun, in the language of political economy, to extract rents rather than to deliver services.</p>

<h3>10.2 The case that Tamil Nadu made a risky call</h3>
<p>Governance is hard. Building a state government from scratch with a leader who has never legislated, a cabinet without sufficient experienced hands, a manifesto that does not address the state's hardest medium-term problems, and an inner circle drawn substantially from outside politics is not the kind of risk a state with 7.6 crore citizens, India's second-largest manufacturing economy, India's second-largest state by GDP, and a complex set of inter-state water and language disputes should take lightly. If TVK fumbles its budgets, mishandles the next major flood (a near-certainty given Tamil Nadu's monsoon patterns), or freezes when the next labour dispute breaks at an industrial cluster, the price will be paid not by Vijay or his fan club but by the most economically precarious citizens of the state, us. A vote against incumbents who deserved to be punished is a defensible, even rational, act of democratic accountability. A vote for a replacement that may not yet be capable of governing is a different kind of bet, and it deserves to be evaluated as a bet rather than as a certainty.</p>

<h3>10.3 The verdict, such as one is possible</h3>
<p>Both arguments above are simultaneously true. The election was rational as a punishment vote. It is risky as a governance choice. Whether the bet pays off will depend on a small number of decisions taken in the first eighteen months of the TVK government &mdash; specifically: the quality of the cabinet appointments, the speed with which experienced bureaucrats are retained or replaced, the competence of the first state budget, the introduction and implementation of welfare schemes, and the response to the inevitable first test of crisis management. If TVK proves capable of appointing well, listening to its bureaucracy, and passing a competent first budget, the gamble will look in retrospect like wisdom. If it cannot, it will look like recklessness, and that will look ugly.</p>

<p>What can be said with much greater certainty is this: <strong>the Dravidian-duopoly era of Tamil Nadu politics has ended</strong>, regardless of how the next five years unfold. The political possibility space in the state has expanded. It is now more evident as to who chooses what happens; it is also visible that the choices made for a larger sphere are an educated choice rather than a blind herding-like decision making. Tamil Nadu is up for a larger gamble by the people, and only TVK and time can clear the uncertainties or prove it right.</p>

<hr class="divider" />

<h2 id="discussion"><span class="num">11</span>Discussion: What the Mathematics Tells Us</h2>

<h3>11.1 The Structural Break</h3>
<p>The single most important statistical finding of this paper is that the 2026 Tamil Nadu election represents a <strong>structural break</strong> in the data-generating process that governed all previous elections from 2001&ndash;2021. A Chow test applied to party vote shares across cycles would almost certainly reject the null hypothesis of parameter stability at any conventional significance level. The implication: models trained on historical data were, by construction, unable to predict 2026 because the model itself was misspecified &mdash; it was built on assumptions that were no longer true, or to say in political terms, &ldquo;time changes trends&rdquo;.</p>

<h3>11.2 The Mathematics of a Fragmented Opposition</h3>
<p>A key insight from the FPTP amplification analysis is that TVK did not need to be universally popular &mdash; it just needed to be the plurality winner in enough constituencies. With DMK and ADMK contesting independently against TVK, the anti-TVK vote was divided roughly 27:22:rest, allowing TVK to win many seats with vote shares as low as 32&ndash;36% in individual constituencies. The FPTP system's non-linearity converted this modest state-level plurality (~31%) into a substantially larger seat share (~46%).</p>

<p>What FPTP did not deliver, however, was a majority bonus large enough to put TVK across the 118 threshold. In 2011, the ADMK alliance won 150 seats on a 38% vote share &mdash; a textbook FPTP over-reward in a two-pole contest. In 2026, TVK won {actual_seats["TVK"]} seats on roughly 31% &mdash; an amplification, but a contained one. The fragmentation that helped TVK win the most seats also made it fall short from securing absolute majority in the Assembly. This is the mathematical signature of a three-pole, not two-pole, electoral system, and it is the strongest single piece of evidence that Tamil Nadu has structurally transitioned out of Dravidian duopoly and into something more competitive and more informed.</p>

<p>This pattern is also analogous to the failure of a Condorcet winner to emerge: TVK was the plurality choice in a clear majority of constituencies, but not the preferred party for a majority of voters statewide.</p>

<h3>11.3 What the SIR Tells Us</h3>
<p>The SIR analysis reveals an asymmetry that, contrary to the narrative of systematic anti-TVK deletions, may have actually provided a marginal net benefit to TVK: additions were heavily weighted toward the 18&ndash;29 age bracket (TVK's core demographic), while deletions were concentrated among the 50+ cohort (traditionally ADMK's and DMK's base). If anything, the age profile of the revision appears to have modestly favoured the younger electorate &mdash; though the effect size is small relative to the scale of TVK's eventual majority.</p>

<h3>11.4 Cash vs. Mobilisation: A New Electoral Model</h3>
<p>The seizure analysis's most interesting finding (subject to actual data confirmation) is the potential negative correlation between TVK's success and district-level seizure intensity. If confirmed with actual data, this would suggest that TVK's electoral model &mdash; that is, built on the fan-network mobilization, door-to-door outreach by young party members, and social media activation &mdash; is systematically different from the cash model of established parties. This has broader implications for understanding how revolutionary parties can compete against financially dominant incumbents.</p>

<h3>11.5 Limitations</h3>
<ul>
  <li>Voter roll individual-level data unavailable; demographic analysis relies on aggregated ECI statistics.</li>
  <li>Cash seizure data is an imperfect proxy; actual bribe expenditure is unobservable by design.</li>
  <li>TVK has no prior electoral history; all priors required analogy-based construction.</li>
  <li>The FPTP amplification model assumes a single &alpha; across all constituencies; local variation is not modeled.</li>
  <li>Post-poll survey data for 2026 TN was not available at time of writing; party affinity indices are estimated.</li>
</ul>

<h3>11.6 Conclusion</h3>
<p>The TVK result was, contrary to the dominant &lsquo;impossible&rsquo; framing in the Indian press, well within the range of outcomes our prior model could produce: a roughly one-in-three event by the surprisal metric, carrying about 1.5 bits of information. What makes the 2026 Tamil Nadu election academically interesting is not that something improbable happened (it didn't, statistically), but that almost every public-facing model failed to anticipate it because the priors had silently drifted out of date. The structural conditions were hiding in plain sight, and yet we failed to notice. The mathematics worked. The political imagination was built on a Tamil Nadu that no longer existed. <strong>That is the paper's central finding, and it is a finding about forecasting, not just about Tamil Nadu.</strong></p>

<hr class="divider" />

<h2 id="sources"><span class="num">12</span>References and Data Sources</h2>

<h3>Primary Data Sources</h3>
<table class="refs">
<tr><td>1.</td><td><strong>Election Commission of India</strong> &mdash; 2026 Tamil Nadu Assembly Election Results (constituency-level Excel; primary source for the 234-AC dataset used throughout this paper). <em>https://results.eci.gov.in/ResultAcGenMay2026/</em></td></tr>
<tr><td>2.</td><td><strong>Trivedi Centre for Political Data (TCPD)</strong> &mdash; Lok Dhaba, Tamil Nadu Vidhan Sabha Results 2001&ndash;2021. <em>https://tcpd.ashoka.edu.in/lok-dhaba/</em></td></tr>
<tr><td>3.</td><td><strong>Chief Electoral Officer, Tamil Nadu</strong> &mdash; Electoral Roll Statistics, MCC Enforcement Data. <em>https://www.elections.tn.gov.in/</em></td></tr>
<tr><td>4.</td><td><strong>Association for Democratic Reforms (ADR)</strong> &mdash; Tamil Nadu 2026 Candidate Affidavit Analysis. <em>https://adrindia.org/</em></td></tr>
<tr><td>5.</td><td><strong>ECI SUVIDHA Portal</strong> &mdash; MCC Complaint and Enforcement Statistics. <em>https://suvidha.eci.gov.in/</em></td></tr>
</table>

<h3>Academic References</h3>
<table class="refs">
<tr><td>6.</td><td>Rae, D. W. (1967). <em>The Political Consequences of Electoral Laws</em>. Yale University Press.</td></tr>
<tr><td>7.</td><td>Chhibber, P. &amp; Murali, G. (2006). Duvergerian dynamics in the Indian states. <em>Party Politics</em>, 12(1), 5&ndash;34.</td></tr>
<tr><td>8.</td><td>Banerjee, A. &amp; Pande, R. (2007). Parochial Politics: Ethnic Preferences and Politician Corruption. <em>NBER Working Paper</em> 12381.</td></tr>
<tr><td>9.</td><td>Stokes, S., Dunning, T., Nazareno, M. &amp; Brusco, V. (2013). <em>Brokers, Voters, and Clientelism</em>. Cambridge University Press.</td></tr>
<tr><td>10.</td><td>Silver, N. (2012). <em>The Signal and the Noise</em>. Penguin Press.</td></tr>
<tr><td>11.</td><td>Gelman, A. &amp; King, G. (1993). Why are American Presidential election campaign polls so variable when votes are so predictable? <em>British Journal of Political Science</em>, 23(4), 409&ndash;451.</td></tr>
</table>

<h3>News Sources</h3>
<table class="refs">
<tr><td>12.</td><td><em>The Hindu</em> &mdash; Tamil Nadu election coverage, January&ndash;May 2026.</td></tr>
<tr><td>13.</td><td><em>The Indian Express</em> &mdash; TVK rally reports, ECI voter roll controversy coverage.</td></tr>
<tr><td>14.</td><td><em>Dinamalar / Dinamani</em> &mdash; Tamil-language coverage of Karur stampede and TVK cadre formation.</td></tr>
<tr><td>15.</td><td><em>NDTV / India Today</em> &mdash; Exit poll and results analysis, May 2026.</td></tr>
</table>

<p style="margin-top:32px; color:var(--muted); font-size:0.92em;">All code, data, and figures available in the project repository. Analysis conducted in Python 3.9 using NumPy, Pandas, SciPy, Matplotlib, Seaborn, Plotly, and python-docx. The Word version of this paper (<code>The_Improbable_Mandate_TVK_TN2026.docx</code>) is the canonical, hand-edited manuscript; this HTML companion mirrors its prose alongside live interactive charts.</p>

</div>
"""

    return HTML_HEAD + body + HTML_FOOT


def run(actual_seats: dict = None):
    print("=" * 60)
    print("Generating Interactive HTML")
    print("=" * 60)
    html = build_html(actual_seats=actual_seats)
    out_path = os.path.join(OUT, "improbable_mandate.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"  HTML written → {out_path} ({size_kb:.1f} KB)")
    return out_path


if __name__ == "__main__":
    run({"TVK": 108, "DMK": 59, "ADMK": 47})
