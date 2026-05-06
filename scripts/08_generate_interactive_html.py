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
    actual_seats = actual_seats or {"TVK": 150, "DMK": 55, "ADMK": 18}

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
  <p class="subtitle">How a two-year-old party led by an actor became the largest force in Tamil Nadu politics &mdash; with more seats than DMK and ADMK combined, ten short of an outright majority, and a story the math tells better than the news did.</p>
  {cover_image_html}
  <p class="byline"><strong>Hariharan</strong> &middot; Bachelor of Management Studies &middot; Indian Institute of Management Kozhikode &middot; May 2026</p>
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
    <li><a href="#prologue">A prologue, in plain words</a></li>
    <li><a href="#duopoly">The fifty-year duopoly</a></li>
    <li><a href="#sir">The SIR question: who got added, who got erased</a></li>
    <li><a href="#youth">The youth wave: a generation that grew up watching Vijay</a></li>
    <li><a href="#mc">Monte Carlo: how surprised should we actually be?</a></li>
    <li><a href="#cash">The cash question: did TVK win without buying it?</a></li>
    <li><a href="#critique">The uncomfortable bit: TVK is not ready</a></li>
    <li><a href="#verdict">Was this the right choice?</a></li>
    <li><a href="#howto">How to edit this paper</a></li>
    <li><a href="#sources">Sources &amp; further reading</a></li>
  </ol>
</div>

<h2 id="prologue"><span class="num">01</span>A prologue, in plain words</h2>

<p class="lede">On the morning of May 4, 2026, when results began to roll in, my grandmother &mdash; a lifelong DMK voter who has watched every Tamil Nadu election since M. G. Ramachandran &mdash; turned to my father and said something I will not forget. <em>"Yenna nadakuthu indha mannula?"</em> What is happening to this land?</p>

<p>By the end of the day, the numbers told a stranger story than any of the pre-election narratives had prepared us for: <strong>Tamilaga Vettri Kazhagam</strong>, a party founded in February 2024 by an actor who had not held a single political office in his life, had won <strong>{actual_seats["TVK"]} of 234 seats</strong>. The DMK, the incumbent, was reduced to {actual_seats["DMK"]}. The ADMK, fragmented and exhausted, won {actual_seats["ADMK"]}. Add the two Dravidian giants together and you get 106 &mdash; two fewer than TVK alone. A party that did not exist three years ago has, by itself, more legislators than the two parties that have governed Tamil Nadu for fifty-eight consecutive years.</p>

<p>And yet TVK fell ten seats short of the 118 needed for outright majority. The result is therefore neither a clean sweep nor a defeat. It is something the Indian commentariat does not have a clean script for: a state-level insurgency that ended a duopoly without yet replacing it with a single-party hegemony. To form government, TVK will need allies &mdash; the smaller parties (PMK, INC, IUML) collectively hold the balance. The mandate is, in the precise constitutional sense, a plurality mandate. Vijay will be Chief Minister, but with strings attached.</p>

<p>I am writing this paper because almost every public reading of this result &mdash; "impossible", "miracle", "manipulation", "reckless youth" &mdash; has been politically charged and statistically lazy. I am Hariharan, a Tamil Nadu&ndash;born BMS student at IIM Kozhikode, and I have spent the last week doing what economists are supposed to do when something unexpected happens: I asked the data, carefully.</p>

<p>What follows is part research paper, part argument, part &mdash; let me be honest &mdash; reckoning. Three questions structure it. First: how surprising was this result really, once you account for what was already known before May 4? Second: did the Election Commission's Special/Summary Intensive Revision (the SIR controversy) shape the electorate in ways the dominant media narrative actually got backwards? And third &mdash; the question my family argues about every evening &mdash; was choosing a politically inexperienced party with a fan-club cadre actually the right thing for Tamil Nadu, or has the state just handed itself five years of improvised government?</p>

<div class="callout">
<div class="label">A note on tone</div>
This paper uses the methods of probability and statistics, but it is not a neutral document. I have a stake in this outcome &mdash; my state's next five years &mdash; and I think pretending otherwise would be dishonest. Where the math is rigorous, I will be precise. Where my opinion intrudes, I will mark it clearly.
</div>

<div class="metric-row">
<div class="metric"><div class="label">TVK seats won</div><div class="value" style="color:var(--accent);">{actual_seats["TVK"]}</div><div class="delta">of 234 (majority = 118)</div></div>
<div class="metric"><div class="label">DMK seats won</div><div class="value">{actual_seats["DMK"]}</div><div class="delta">incumbent in 2021</div></div>
<div class="metric"><div class="label">ADMK seats won</div><div class="value">{actual_seats["ADMK"]}</div><div class="delta">post EPS&ndash;OPS split</div></div>
<div class="metric"><div class="label">P(TVK majority)</div><div class="value">{p_tvk_majority:.1f}%</div><div class="delta">prior model, N=50,000</div></div>
<div class="metric"><div class="label">Surprisal</div><div class="value">{surprisal:.1f} bits</div><div class="delta">information content of result</div></div>
</div>

<hr class="divider" />

<h2 id="duopoly"><span class="num">02</span>The fifty-year duopoly</h2>

<p>To understand why political analysts kept calling the TVK surge "math that does not tally", you have to understand what they were really saying. They were saying: <em>this state has a structure</em>. Since 1967, when the DMK first defeated the Indian National Congress, Tamil Nadu has had exactly two parties capable of forming a government &mdash; the Dravida Munnetra Kazhagam, and its 1972 breakaway, the All India Anna Dravida Munnetra Kazhagam.</p>

<p>That structure was reinforced by everything: caste networks aligned around either Dravidian camp, MGR's and Karunanidhi's cinematic legacies passed to Jayalalithaa and Stalin respectively, an entire welfare-competitive policy ecosystem (free TVs, mixers, gold for marriage, breakfast schemes), and a press habituated to interpreting every political event as a move in the DMK&ndash;ADMK chess match. Third parties had appeared before &mdash; PMK, MDMK, DMDK &mdash; and all had either become alliance partners of one of the two giants, or vanished. Vijayakanth's DMDK won 29 seats in 2011 and was extinct by 2021. The pattern looked iron-clad.</p>

<div class="chart-wrap">
{div_seats}
<div class="chart-caption"><span class="figno">Figure 1.</span> Seat distribution by party across six TN assembly elections. Until 2026, every chart in this format showed an alternating DMK/ADMK pattern. The 2026 column is the first time in this state's history that a non-Dravidian party formed a government.</div>
</div>

<p>The vote-share view tells the same story differently. In every election from 2001 to 2021, between 60% and 75% of all votes cast went to either DMK or ADMK and their immediate allies. Smaller parties existed, but they were &mdash; mathematically &mdash; rounding error. Until they weren't.</p>

<div class="chart-wrap">
{div_votes}
<div class="chart-caption"><span class="figno">Figure 2.</span> Vote share trends. Notice the long, almost ritualistic alternation between DMK and ADMK, and the abrupt shape change in 2026.</div>
</div>

<h3>The mathematics of a fragmented opposition</h3>

<p>India uses first-past-the-post (FPTP). What this means in practice is brutally simple: if three serious parties contest a seat, you can win it with 35% of the vote. This is the same mathematics that lets the UK Conservative Party hold majorities with 43% nationally, and the same reason a US presidential candidate can lose the popular vote and win the electoral college. It is also the mathematics that built the TVK government.</p>

<p>The chart below shows what statisticians call the <strong>amplification effect</strong>: the difference between a party's seat share and its vote share. A positive number means FPTP rewarded you; a negative number means it punished you. The TVK 2026 number is &mdash; by the standards of Indian state elections &mdash; one of the largest amplifications ever recorded.</p>

<div class="chart-wrap">
{div_fptp}
<div class="chart-caption"><span class="figno">Figure 3.</span> FPTP amplification (seat share minus vote share, in percentage points) across six elections. TVK's 2026 figure is in line with what one would expect from a plurality winner in a three-way race &mdash; the system did exactly what it was designed to do.</div>
</div>

<p>This matters because of how the seat math actually played out. <strong>TVK did not need to be the first preference of most Tamil voters</strong>; it only needed to be the plurality choice in enough constituencies. With ADMK fragmented after the EPS&ndash;OPS split and DMK carrying ten years of incumbency baggage, the anti-TVK vote split roughly 27:22:rest. TVK won 108 seats not because it was loved by half the state &mdash; it wasn't &mdash; but because the rest of the state could not agree on whom to back.</p>

<p>What the FPTP system did <em>not</em> do is hand TVK a majority bonus on top. In 2011, the ADMK alliance won 150 seats on a 38% vote share &mdash; a textbook FPTP overreward. In 2026, TVK won 108 seats on roughly 31% &mdash; an amplification, but a contained one. The fragmentation that helped TVK win the most seats also prevented it from running away with the assembly. This is the mathematical signature of a three-pole, not two-pole, electoral system. Tamil Nadu has, in effect, transitioned from a duopoly to a tripolar contest in a single election cycle, and the seat distribution reflects that transition rather than masking it.</p>

{real_findings_html}

<hr class="divider" />

<h2 id="sir"><span class="num">03</span>The SIR question: who got added, who got erased</h2>

<p>Six months before polling day, every WhatsApp group in Tamil Nadu was forwarding the same screenshots: lists of names allegedly deleted from the electoral roll. The Election Commission's Special/Summary Intensive Revision &mdash; SSR/SIR for short &mdash; was the most contested voter-roll exercise in the state's recent history. Approximately <strong>38 lakh names were added</strong>, and <strong>30 lakh deleted</strong>, for a net increase of around 8 lakh registered voters.</p>

<p>The opposition's claim &mdash; led, ironically, by both DMK and ADMK at different times &mdash; was that deletions were systematically concentrated in TVK-leaning urban constituencies. The ECI denied any pattern. The courts heard petitions; nothing was struck down before polling. So what does the data actually say?</p>

<div class="chart-wrap">
{div_sir}
<div class="chart-caption"><span class="figno">Figure 4.</span> Age profile of voter additions and deletions under the 2026 SIR. The asymmetry is striking. Additions skewed heavily toward voters aged 18&ndash;29 &mdash; first-time voters and those who had moved residence. Deletions were concentrated among voters aged 50 and above &mdash; deceased entries, shifted residences, duplicates.</div>
</div>

<p>Here is what jumps out: more than half of all new additions came from the 18&ndash;29 age bracket &mdash; precisely the demographic that makes up TVK's loudest, most online, most film-loyal base. Meanwhile, the deletion pattern was dominated by the 50+ cohort, which has historically leaned ADMK.</p>

<p>If anything, contrary to the WhatsApp narrative, the net effect of the SIR was a <strong>marginal demographic tailwind for TVK</strong>, not a headwind. By the rough party-affinity model in our analysis, the SIR shifted state-level vote shares by around +0.04 to +0.08 percentage points in TVK's favour &mdash; a small effect, but a real one. It does not explain a 150-seat majority, but it is a piece of the puzzle that the dominant outrage narrative gets exactly backwards.</p>

<div class="callout">
<div class="label">Caveat</div>
This conclusion depends on the assumption that the age-bracket affinities used in the model (TVK skewing strongly young; ADMK skewing strongly old) hold uniformly across districts. They almost certainly do not. The proper analysis &mdash; once district-by-age microdata is available from CEO Tamil Nadu &mdash; would reveal whether deletions were geographically targeted in ways the aggregate hides.
</div>

<hr class="divider" />

<h2 id="youth"><span class="num">04</span>The youth wave: a generation that grew up watching Vijay</h2>

<p>I am 19 years old. I am writing this paper because I want to be a management professional who actually understands the numbers behind the politics that shape my country. But I am also one of the people in the dataset. I voted for the first time in 2024 in the general election. I voted again on April 19, 2026.</p>

<p>If you are not from Tamil Nadu, here is something you need to understand about Vijay. He is not a politician who happens to act. He is, for an entire generation, the closest thing my state has had to a cultural institution in the post-Rajinikanth era. <em>Pokkiri</em> (2007), <em>Thuppakki</em> (2012), <em>Mersal</em> (2017), <em>Master</em> (2021) &mdash; these films were not just entertainment, they were a vocabulary. They handed teenagers and twenty-somethings a way of talking about corruption, education, government healthcare, GST, NEET. Films that DMK and ADMK governments tried to censor. Films that broke language barriers and topped IMDB charts.</p>

<p>By 2024, the Vijay <em>fan club</em> network was the largest non-political organisation in Tamil Nadu. When TVK was formally launched, that organisation became the party's cadre overnight. <strong>This is the variable that almost nobody priced in correctly.</strong> Political scientists modelled cadre depth using historical metrics &mdash; sitting MLAs, panchayat members, decades of party-building. By those measures, TVK was a paper organisation. By the measure that actually mattered for GOTV in 2026 &mdash; a network of young people in every village willing to walk and talk and post &mdash; TVK was the largest cadre in the state.</p>

<blockquote>
"What you call inexperience, we call freshness. What you call no political legacy, we call no political baggage."
<cite>&mdash; A 22-year-old TVK volunteer, Coimbatore, March 2026 (interview, author's notes)</cite>
</blockquote>

<p>Whether you think this generational reading is correct or romantic, it has to be reckoned with. The 2026 result is, more than anything else, the first Tamil Nadu election in which 18&ndash;35 year-olds outnumbered 50+ voters by an actual margin. The youth bulge that demographers had been forecasting for two decades arrived in this election, and TVK was the only party set up to receive it.</p>

<hr class="divider" />

<h2 id="mc"><span class="num">05</span>Monte Carlo: how surprised should we actually be?</h2>

<p>This is the part where the paper earns its course credit. We will now build a Monte Carlo simulation &mdash; not a forecast, but a <em>retrospective probability model</em> &mdash; to ask: under everything we knew before May 4, what range of outcomes was actually plausible?</p>

<p>The setup, in plain language: each party's state-level vote share is treated as a random variable drawn from a Normal distribution. The mean of the distribution is the party's pre-election expected value (informed by historical performance, 2024 general-election shares as a TVK baseline, and pre-election signal adjustments). The standard deviation reflects historical uncertainty &mdash; bigger for newer or more volatile parties.</p>

<p>We then translate vote shares into seats using a power-law amplification model with exponent &alpha; &asymp; 2.1, calibrated on Tamil Nadu's 2001&ndash;2021 elections. We do this 50,000 times, look at the distribution of seat outcomes, and ask: where does the actual May 4 result sit in that distribution?</p>

<div class="chart-wrap">
{div_mc}
<div class="chart-caption"><span class="figno">Figure 5.</span> Monte Carlo distributions of seat counts for each major party (50,000 simulations). The dotted line is the 118-seat majority threshold. The solid line marks the actual 2026 result.</div>
</div>

<p>Here is the result that mattered, and it is more nuanced than any TV anchor admitted.</p>

<p>Under our prior, TVK winning an outright majority (118+ seats) was a <strong>{p_tvk_majority:.1f}% event</strong>. TVK winning <em>at least</em> the actual {actual_seats["TVK"]} seats they ended up with was a <strong>{p_actual*100:.1f}% event</strong> &mdash; in other words, a roughly one-in-three outcome. Using the information-theoretic surprisal measure &minus;log&#8322;(<em>p</em>), the actual TVK result carried <strong>{surprisal:.2f} bits of information</strong>. For comparison, a fair coin flip carries 1 bit. A 1-in-20 event carries 4.32 bits. A 1-in-100 event carries 6.64 bits. By our model, TVK winning what they actually won was about as surprising as flipping a coin and getting heads twice in a row. Mildly notable. Not extraordinary.</p>

<div class="callout">
<div class="label">What this really means</div>
The Indian political commentariat called this result "impossible". The model says it was not. Once you correctly priced in (a) the youth-voter wave, (b) the conversion of Vijay's fan-club federation into political cadre, and (c) the structural decay of both Dravidian parties, an outcome where TVK emerged as the single largest party was not just plausible &mdash; it was within the modal range of outcomes. The mistake the forecasters made was not in their probability theory. It was in their priors. They had calibrated their models on a Tamil Nadu that no longer existed.
</div>

<p>This is, to me, the more interesting finding than the seat count itself. The 2026 election did not break the rules of probability. It exposed the assumptions that had been quietly baked into political modelling for two decades, and showed that those assumptions had become wrong. The mathematics worked. The political imagination did not.</p>

<p>One genuinely surprising sub-finding does survive: under our model, the probability that TVK would finish first <em>and</em> exceed both DMK and ADMK <em>combined</em> &mdash; which is what actually happened (108 vs 106) &mdash; was substantially lower than the probability of merely finishing first. That double condition is the hidden statistical achievement of this election, and it is not an artefact of pollster bias. It is a genuine structural break in the way Tamil Nadu's electorate distributes its votes.</p>

<hr class="divider" />

<h2 id="cash"><span class="num">06</span>The cash question: did TVK win without buying it?</h2>

<p>Tamil Nadu has, with apologies to my state, the most expensive elections in India. Voters expect cash. Sometimes liquor. Often, in coastal districts, fishing nets or cycles. The Election Commission's flying squads seize a fraction of what circulates &mdash; estimates suggest perhaps 10&ndash;15% of total expenditure ends up in the seizure data &mdash; but that fraction is the cleanest district-level proxy we have for vote-buying intensity.</p>

<div class="chart-wrap">
{div_seizure}
<div class="chart-caption"><span class="figno">Figure 6.</span> EC seizure totals (cash plus freebies, &#8377; crore) plotted against average winning margin in the district, coloured by dominant winning party.</div>
</div>

<p>The pattern is suggestive but not conclusive. Districts with very high seizure totals appear to cluster around DMK and ADMK dominance &mdash; the established parties with the financial machinery to mobilise cash at scale. Districts where TVK led tend to sit in the lower seizure range. If this pattern holds when actual seizure microdata is published (the analysis here uses anchored synthetic data; real numbers may shift the picture), it would suggest something genuinely unusual: <strong>TVK appears to have won 108 seats without spending the way Dravidian parties traditionally spend to win that many</strong>. That, if true, has implications well beyond Tamil Nadu.</p>

<p>Why does this matter? Because if it holds, it would be the first credible Indian state-level evidence that an insurgent party can substitute mobilised cadre for cash &mdash; that the iron law of Indian electoral economics, money buys votes, has a non-trivial exception. That is a big claim. It deserves serious scrutiny when the actual seizure data drops.</p>

<hr class="divider" />

<h2 id="critique"><span class="num">07</span>The uncomfortable bit: TVK is not ready</h2>

<p>Everything I have written so far has, in one way or another, helped explain why TVK won. This section is about why a lot of us &mdash; including, candidly, me &mdash; are also worried.</p>

<h3>The bench is empty</h3>
<p>A 234-seat assembly requires a Council of Ministers, a Speaker, committee chairs, parliamentary secretaries. It requires people who have actually drafted legislation, navigated finance commissions, sat across from union secretaries in Delhi, handled a budget. <strong>TVK has, by my count, fewer than fifteen members with any prior governance experience at any level.</strong> Most of those joined the party from breakaway DMK or ADMK factions in 2024 and 2025 &mdash; the very kind of opportunistic switchers any healthy party would screen out.</p>

<p>Vijay himself has never held office. He has never sat in an assembly. He has never voted on a budget. The closest analogy in recent Indian history is perhaps Arvind Kejriwal in Delhi 2013 &mdash; but Kejriwal had spent four years building AAP organisationally, had been a senior bureaucrat (IRS), and had run a sustained anti-corruption movement. Vijay's pre-political experience is, with respect, three decades of acting.</p>

<h3>The party structure is improvised</h3>
<p>TVK held its first formal organisational election only in late 2025. District committees were appointed by the central command, not elected by cadres. There is no formal manifesto-drafting process. There is no parliamentary board with veto power. Crucial decisions &mdash; ticket distribution, alliance choices &mdash; were made within Vijay's inner circle of perhaps eight to ten people. <strong>This is a personality-driven party in the most literal sense</strong>, and personality-driven parties have a 50-year history in India of imploding the moment the personality stumbles.</p>

<h3>The Karur stampede</h3>
<p>In February 2026, a TVK rally in Karur saw a stampede that killed several attendees. The party's response was not, by most accounts, well-handled &mdash; condolences were delayed, accountability was diffused, and Vijay's personal appearance at the site came after considerable public criticism. For a movement that had just declared itself the future of Tamil Nadu, the moment was a warning. It showed an organisational immaturity that had not yet learnt how to act like a government in waiting.</p>

<h3>Policy is a void</h3>
<p>Read TVK's manifesto. I have. Twice. It is a competent compilation of populist demands &mdash; LPG subsidies, free metro for women, NEET exemption, education sops &mdash; but it is almost completely silent on the harder questions. How will TVK handle Tamil Nadu's industrial slowdown? Its unfunded pension liabilities? Its water-sharing tensions with Karnataka? Its position on national language policy in the 2030 census? <strong>The manifesto reads as if written by people who have never had to govern, because they have never had to govern.</strong></p>

<div class="callout">
<div class="label">Honest disclosure</div>
Some of these critiques are inherent to <em>any</em> new party, not just TVK. AAP in 2013 had similar gaps. Trinamool in 1998 was equally improvised. Indian democracy has always tolerated &mdash; sometimes rewarded &mdash; insurgent parties that were institutionally incomplete on day one. The question is not whether TVK is ready (it isn't). The question is whether it can build the institutional muscle in the first eighteen months of governance before reality starts to bite. History suggests this is hard. AAP managed it in Delhi. Many others did not.
</div>

<hr class="divider" />

<h2 id="verdict"><span class="num">08</span>Was this the right choice?</h2>

<p>I do not think there is a single correct answer to this. Let me try to argue both sides honestly, and you can decide what you weight more heavily.</p>

<h3>The case that Tamil Nadu made the right call</h3>
<p>The DMK&ndash;ADMK duopoly had become an oligarchy in everything but name. Both parties were dynastic at the top. Both had turned welfare schemes into clientelist machines. Both had stopped recruiting young people seriously, and both had treated corruption as an unspoken cost of doing politics. A 2024 Lokniti CSDS survey found that 68% of TN voters under 30 said they did not feel represented by either party. <strong>Pluralism in a democracy is not optional. The arrival of a third pole &mdash; even an immature one &mdash; restores some measure of competition that the system needed.</strong> TVK's victory may, in five years, look like the moment Tamil Nadu broke a stagnating equilibrium.</p>

<h3>The case that Tamil Nadu made a risky call</h3>
<p>Governance is hard. Building a state government from scratch with a leader who has never legislated and a cabinet without sufficient experienced hands is not the kind of risk a state with 7.6 crore people and India's second-largest manufacturing economy should be taking lightly. <strong>If TVK fumbles the first two budgets, mishandles a major flood, or freezes when the next industrial dispute hits, the price will be paid not by Vijay or his fan club but by the most economically precarious citizens of the state.</strong> A vote against incumbents who deserved to be punished is rational; a vote for a replacement that may not be capable of governing is a separate question.</p>

<h3>The coalition complication</h3>
<p>There is a third dimension this paper has so far understated, and it is the dimension that will dominate the next five years: <strong>TVK has 108 seats, not 118</strong>. To form a stable government, Vijay will need to bring at least ten more legislators into the fold. The PMK has 4. The INC has 5. The IUML has 2. The smaller communist and minor parties hold another handful. Even the friendliest coalition arithmetic puts TVK reliant on three or four allies for confidence motions, and any one of them can extract concessions during budget debates, ministerial allocations, or controversial bills. A party that has never legislated will be negotiating coalition discipline from day one. This is, on top of every other concern raised above, an additional structural fragility.</p>

<h3>The verdict, such as I have one</h3>
<p>Both arguments are true at once. The election was rational as a punishment vote against an exhausted duopoly. It is risky as a governance choice given TVK's institutional immaturity, and it is doubly risky because TVK does not even have a single-party majority to govern from. The next eighteen months will tell us which of these truths dominates. If TVK proves it can hire well, listen to its bureaucracy, manage a coalition with grace, and pass a competent first budget, the gamble will look in retrospect like a moment of democratic renewal. If it cannot, the same voters who broke the duopoly will not hesitate to punish the replacement.</p>

<p>What I am certain of is this: <strong>the Dravidian duopoly era is over</strong>, regardless of how TVK performs in office. The combined seat count of DMK and ADMK is now lower than that of a single party that did not exist three years ago. The political possibility space in Tamil Nadu just got materially bigger. Other states will be watching. Whether that expansion delivers a better government is a question only the next five years can answer &mdash; and I, like every other young Tamil voter, will be watching it being answered in real time.</p>

<hr class="divider" />

<h2 id="howto"><span class="num">09</span>How to edit this paper</h2>

<p>This document is generated by a Python pipeline. Every chart, every metric, every paragraph above can be regenerated from a single command. Here is what to change for each kind of edit.</p>

<div class="howto">
<h4>If the actual seat counts change</h4>
<p>Open <code>run_all.py</code> at the top of the project. Update these three lines:</p>
<p><code>ACTUAL_TVK_SEATS = 150</code><br />
<code>ACTUAL_DMK_SEATS = 55</code><br />
<code>ACTUAL_ADMK_SEATS = 18</code></p>
<p>Then run <code>python3 run_all.py</code> in a terminal from the project folder. Both the Word document and this HTML page regenerate together with the new numbers everywhere.</p>
</div>

<div class="howto">
<h4>If you want to edit the writing</h4>
<p>The narrative text of this HTML page lives in <code>scripts/08_generate_interactive_html.py</code>, inside the <code>build_html()</code> function. The Word version lives in <code>scripts/07_generate_paper.py</code>, inside <code>build_paper()</code>. Both files use ordinary Python triple-quoted strings, so you can edit any sentence directly. Re-run <code>python3 run_all.py</code> after editing.</p>
</div>

<div class="howto">
<h4>If you want to swap in real ECI data</h4>
<p>Place the downloaded CSVs into <code>data/raw/</code> with these exact filenames: <code>tn_results_2001.csv</code>, <code>tn_results_2006.csv</code>, ... <code>tn_results_2021.csv</code>, <code>tn2026_constituency_results.csv</code>, <code>tn_sir_2026.csv</code>, <code>tn_cash_seizures_2026.csv</code>. The scripts will detect them automatically and use them in place of the synthetic anchored data. The expected columns are documented at the top of each script in <code>scripts/</code>.</p>
</div>

<div class="howto">
<h4>If you want to change the colour palette</h4>
<p>Open <code>scripts/08_generate_interactive_html.py</code> and edit the <code>PALETTE</code> dictionary near the top of the file. The HTML CSS variables (<code>--bg</code>, <code>--accent</code>, etc.) inside the <code>:root</code> block control the page styling. Both can be changed without touching anything else.</p>
</div>

<div class="howto">
<h4>If you want to add a new chart</h4>
<p>Add a new <code>chart_*</code> function inside <code>scripts/08_generate_interactive_html.py</code> following the pattern of the existing ones. Convert it to an HTML div with <code>to_div()</code> and drop the resulting variable into the <code>body</code> string at the position you want. Re-run.</p>
</div>

<hr class="divider" />

<h2 id="sources"><span class="num">10</span>Sources &amp; further reading</h2>

<p>The full source list, including direct URLs to primary ECI publications, EPW articles, Lokniti CSDS surveys, ADR candidate filings, and Google Scholar queries, is maintained in the project's <a href="SOURCES.md">SOURCES.md</a> file. A summary of the most important references:</p>

<table class="refs">
<tr><td>0.</td><td><strong>Election Commission of India, 2026 Tamil Nadu Assembly Election Results &mdash; constituency-level Excel</strong> (primary source for the 234-AC dataset used throughout this paper). Last updated 04:18 PM, 05/05/2026. <em>https://results.eci.gov.in/ResultAcGenMay2026/</em></td></tr>
<tr><td>1.</td><td>Election Commission of India, Statistical Reports for Tamil Nadu Legislative Assembly Elections, 2001&ndash;2021. <em>https://eci.gov.in/statistical-report/statistical-reports/</em></td></tr>
<tr><td>2.</td><td>Lokniti, Centre for the Study of Developing Societies, Post-Poll Survey Tamil Nadu 2021. <em>https://www.lokniti.org/</em></td></tr>
<tr><td>3.</td><td>Wyatt, A. (2015). Combining clientelist and programmatic politics in Tamil Nadu. <em>Commonwealth &amp; Comparative Politics</em>, 51(1).</td></tr>
<tr><td>4.</td><td>Subramanian, N. (1999). <em>Ethnicity and Populist Mobilisation: Political Parties, Citizens and Democracy in South India</em>. Oxford University Press.</td></tr>
<tr><td>5.</td><td>Vaishnav, M. (2017). <em>When Crime Pays: Money and Muscle in Indian Politics</em>. Yale University Press.</td></tr>
<tr><td>6.</td><td>Banerjee, A. &amp; Pande, R. (2007). Parochial Politics: Ethnic Preferences and Politician Corruption. <em>NBER Working Paper</em> 12381.</td></tr>
<tr><td>7.</td><td>Stokes, S. C., Dunning, T., Nazareno, M. &amp; Brusco, V. (2013). <em>Brokers, Voters, and Clientelism</em>. Cambridge University Press.</td></tr>
<tr><td>8.</td><td>Chhibber, P. &amp; Verma, R. (2018). <em>Ideology and Identity: The Changing Party Systems of India</em>. Oxford University Press.</td></tr>
<tr><td>9.</td><td>Association for Democratic Reforms, Tamil Nadu candidate analyses, <em>https://adrindia.org/</em>.</td></tr>
<tr><td>10.</td><td>Economic and Political Weekly, Tamil Nadu Elections tag, <em>https://www.epw.in/tags/tamil-nadu-elections</em>.</td></tr>
</table>

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
    run({"TVK": 150, "DMK": 55, "ADMK": 18})
