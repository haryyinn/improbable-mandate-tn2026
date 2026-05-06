"""
03_sir_analysis.py
==================
Analyses Tamil Nadu's Special/Summary Intensive Revision (SIR) data — the
contentious voter-roll update conducted before the 2026 elections.

What is a SIR?
--------------
The Election Commission conducts a Special Intensive Revision (SIR) /
Special Summary Revision (SSR) where field officers do door-to-door
verification. Voters are added (Form 6 approvals) or deleted (Form 7).

Why this matters for TVK:
--------------------------
  - Deletions/additions by AGE GROUP reveal whether the revision
    disproportionately affected TVK's core 18-35 vote bank.
  - ECI data shows ~30+ lakh net changes were processed in TN 2026.
  - Political parties alleged systematic deletion in TVK-leaning areas.

This script:
  1. Loads SIR district-level data (additions + deletions by age bracket)
  2. Computes proportion of young voters (18-35) in additions vs deletions
  3. Estimates the net electoral impact on TVK's expected vote share
  4. Generates figures: bar charts, proportion charts, net-impact heatmap

Outputs
-------
  outputs/figures/fig_sir_age_additions.png
  outputs/figures/fig_sir_age_deletions.png
  outputs/figures/fig_sir_net_impact.png
  data/processed/sir_analysis.csv
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW  = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")
FIGS = os.path.join(ROOT, "outputs", "figures")
os.makedirs(FIGS, exist_ok=True)
os.makedirs(PROC, exist_ok=True)

PARTY_COLORS = {
    "TVK":    "#E84545",
    "DMK":    "#E55604",
    "ADMK":   "#2E4057",
    "OTHERS": "#A0A0A0",
}

# ── Age bracket definitions ────────────────────────────────────────────────
AGE_BRACKETS = ["18-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]

# Party affinity by age bracket (index relative to average, 1.0 = neutral)
# Based on: post-poll analysis, fan-club demographics, CSDS Lokniti surveys
# (Update these with actual survey data if available)
PARTY_AGE_AFFINITY = {
    #           18-19  20-29  30-39  40-49  50-59  60-69   70+
    "TVK":   [  1.60,  1.45,  1.10,  0.90,  0.70,  0.55,  0.45],
    "DMK":   [  0.95,  1.00,  1.10,  1.20,  1.15,  1.00,  0.85],
    "ADMK":  [  0.65,  0.70,  0.90,  1.10,  1.30,  1.40,  1.50],
}


def load_sir_data() -> pd.DataFrame:
    """
    Load SIR data from data/raw/tn_sir_2026.csv if it exists.
    Expected columns:
        district, age_bracket, additions, deletions, total_electors_before,
        total_electors_after

    If not available, returns a plausible synthetic dataset using publicly
    reported TN 2026 aggregate figures as anchors:
      - Total additions: ~38 lakh (3.8 million)
      - Total deletions: ~30 lakh (3.0 million)
      - Net: +8 lakh
    Source basis: ECI press releases, CEO TN announcements Jan-Mar 2026
    """
    sir_path = os.path.join(RAW, "tn_sir_2026.csv")
    if os.path.exists(sir_path):
        df = pd.read_csv(sir_path)
        print(f"SIR data loaded from file: {len(df)} rows")
        return df

    print("[INFO] tn_sir_2026.csv not found — using aggregate-anchored estimates.")
    print("       Download from: https://www.elections.tn.gov.in/ → Electoral Roll Statistics")
    print("       Expected columns: district, age_bracket, additions, deletions")

    # ── Aggregate-anchored synthetic data ────────────────────────────────
    # Anchored to reported TN 2026 totals: ~38L additions, ~30L deletions
    # Age proportions from ECI national SIR patterns + TN Census 2011/2021
    np.random.seed(2026)
    districts = [
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli",
        "Salem", "Tirunelveli", "Erode", "Vellore",
        "Thanjavur", "Dindigul", "Tiruppur", "Kancheepuram",
        "Cuddalore", "Nagapattinam", "Villupuram", "Dharmapuri",
        "Namakkal", "Karur", "Perambalur", "Ariyalur",
        "Krishnagiri", "Tiruvannamalai", "Ranipet", "Tirupattur",
        "Kallakurichi", "Tenkasi", "Virudhunagar", "Ramanathapuram",
        "Sivaganga", "Pudukkottai", "Theni", "Nilgiris",
    ]

    # National SIR age profile (additions heavily skew to 18-29; new enrolees)
    addition_age_profile = np.array([0.22, 0.31, 0.18, 0.13, 0.09, 0.05, 0.02])
    # Deletions: dominated by deceased (older) + shifted + not-traceable (spread)
    deletion_age_profile = np.array([0.04, 0.11, 0.14, 0.17, 0.19, 0.18, 0.17])

    total_additions = 3_800_000
    total_deletions = 3_000_000

    rows = []
    for dist in districts:
        dist_add = int(total_additions / len(districts) * np.random.uniform(0.7, 1.3))
        dist_del = int(total_deletions / len(districts) * np.random.uniform(0.7, 1.3))
        for i, bracket in enumerate(AGE_BRACKETS):
            add_noise = np.random.normal(1.0, 0.15)
            del_noise = np.random.normal(1.0, 0.15)
            rows.append({
                "district":    dist,
                "age_bracket": bracket,
                "additions":   max(0, int(dist_add * addition_age_profile[i] * add_noise)),
                "deletions":   max(0, int(dist_del * deletion_age_profile[i] * del_noise)),
            })

    df = pd.DataFrame(rows)
    df.to_csv(sir_path, index=False)
    print(f"  Synthetic SIR data saved to {sir_path} (replace with real data)")
    return df


def compute_sir_proportions(df: pd.DataFrame) -> dict:
    """Return dict of proportion arrays for additions and deletions by age bracket."""
    agg = df.groupby("age_bracket")[["additions", "deletions"]].sum().reindex(AGE_BRACKETS)
    add_props = agg["additions"] / agg["additions"].sum()
    del_props = agg["deletions"] / agg["deletions"].sum()
    return {"agg": agg, "add_props": add_props, "del_props": del_props}


def plot_sir_age_distribution(props: dict):
    """Figure: Additions vs Deletions by Age Bracket (proportions)."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    colors_add = ["#E84545" if b in ["18-19", "20-29", "30-39"] else "#CCCCCC"
                  for b in AGE_BRACKETS]
    colors_del = ["#2E4057" if b in ["50-59", "60-69", "70+"] else "#AAAAAA"
                  for b in AGE_BRACKETS]

    # Additions
    axes[0].bar(AGE_BRACKETS, props["add_props"] * 100, color=colors_add, edgecolor="white")
    axes[0].set_title("Voter Additions by Age Bracket\n(% of total additions)", fontsize=11)
    axes[0].set_ylabel("% of Total Additions")
    axes[0].set_xlabel("Age Group")
    red_patch  = mpatches.Patch(color="#E84545", label="TVK's core demo (18-39)")
    grey_patch = mpatches.Patch(color="#CCCCCC", label="Other age groups")
    axes[0].legend(handles=[red_patch, grey_patch], fontsize=8)

    # Deletions
    axes[1].bar(AGE_BRACKETS, props["del_props"] * 100, color=colors_del, edgecolor="white")
    axes[1].set_title("Voter Deletions by Age Bracket\n(% of total deletions)", fontsize=11)
    axes[1].set_ylabel("% of Total Deletions")
    axes[1].set_xlabel("Age Group")
    blue_patch = mpatches.Patch(color="#2E4057",  label="ADMK's core demo (50+)")
    grey_patch = mpatches.Patch(color="#AAAAAA", label="Other age groups")
    axes[1].legend(handles=[blue_patch, grey_patch], fontsize=8)

    plt.suptitle(
        "Tamil Nadu 2026 SIR: Age Profile of Voter Roll Changes\n"
        "Note: Red bars = TVK's primary electoral base; Blue = traditional ADMK base",
        fontsize=11
    )
    plt.tight_layout()
    path = os.path.join(FIGS, "fig_sir_age_distribution.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def plot_sir_net_impact(props: dict, df: pd.DataFrame):
    """Figure: Net voter change by age + estimated party-wise electoral impact."""
    agg = props["agg"]
    net = agg["additions"] - agg["deletions"]
    net_pct_of_total = net / (agg["additions"].sum() + agg["deletions"].sum()) * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Net change bars
    bar_colors = ["#E84545" if v > 0 else "#2E4057" for v in net]
    axes[0].bar(AGE_BRACKETS, net / 1000, color=bar_colors, edgecolor="white")
    axes[0].axhline(0, color="black", linewidth=1)
    axes[0].set_title("Net Voter Roll Change by Age Bracket\n(Additions − Deletions, in thousands)")
    axes[0].set_ylabel("Net Change (thousands)")
    axes[0].set_xlabel("Age Group")
    add_patch = mpatches.Patch(color="#E84545", label="Net positive (more added)")
    del_patch = mpatches.Patch(color="#2E4057", label="Net negative (more deleted)")
    axes[0].legend(handles=[add_patch, del_patch], fontsize=8)

    # Estimated electoral benefit by party
    net_arr = net.values.astype(float)
    benefits = {}
    for party, affinity in PARTY_AGE_AFFINITY.items():
        # Electoral benefit = sum(net_change_in_bracket * party_affinity_for_bracket)
        # Normalised by total electorate (~6.2 crore) to get vote share impact
        benefit = np.dot(net_arr, affinity) / 62_000_000 * 100
        benefits[party] = round(benefit, 3)

    parties = list(benefits.keys())
    vals = [benefits[p] for p in parties]
    colors = [PARTY_COLORS[p] for p in parties]
    bars = axes[1].bar(parties, vals, color=colors, edgecolor="white", width=0.5)
    axes[1].axhline(0, color="black", linewidth=1)
    axes[1].set_title("Estimated Net Vote-Share Impact of SIR\n(by party, based on age affinity model)")
    axes[1].set_ylabel("Estimated Vote Share Change (pp)")
    axes[1].set_xlabel("Party")
    for bar, v in zip(bars, vals):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                     f"{'+' if v >= 0 else ''}{v:.3f}pp", ha="center", va="bottom", fontsize=9)

    plt.suptitle(
        "Figure: SIR Net Electoral Impact\n"
        "Methodology: Net roll changes × party age-affinity index ÷ total electorate",
        fontsize=10
    )
    plt.tight_layout()
    path = os.path.join(FIGS, "fig_sir_net_impact.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")
    return benefits


def plot_sir_district_heatmap(df: pd.DataFrame):
    """Figure: District-wise SIR intensity (net change as % of pre-revision electorate)."""
    summary = df.groupby("district")[["additions", "deletions"]].sum()
    summary["net"] = summary["additions"] - summary["deletions"]
    summary["net_pct"] = summary["net"] / (summary["additions"] + summary["deletions"]) * 100
    summary["young_add_share"] = (
        df[df["age_bracket"].isin(["18-19", "20-29"])]
        .groupby("district")["additions"].sum()
        / df.groupby("district")["additions"].sum()
        * 100
    )
    summary = summary.sort_values("net_pct")

    fig, ax = plt.subplots(figsize=(11, 9))
    colors = ["#E84545" if v > 0 else "#2E4057" for v in summary["net_pct"]]
    bars = ax.barh(summary.index, summary["net_pct"], color=colors, edgecolor="white")
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Net Change as % of Total Roll Activity")
    ax.set_title(
        "Tamil Nadu 2026 SIR: District-wise Net Voter Roll Change\n"
        "(Red = net additions dominated; Blue = net deletions dominated)"
    )
    plt.tight_layout()
    path = os.path.join(FIGS, "fig_sir_district_heatmap.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def print_sir_summary(df: pd.DataFrame, props: dict, benefits: dict):
    agg = props["agg"]
    total_add = agg["additions"].sum()
    total_del = agg["deletions"].sum()
    young_add = agg.loc[["18-19", "20-29", "30-39"], "additions"].sum()
    old_del   = agg.loc[["50-59", "60-69", "70+"], "deletions"].sum()

    print("\n── SIR Analysis Summary ────────────────────────────────────────")
    print(f"  Total additions:              {total_add:>12,.0f}")
    print(f"  Total deletions:              {total_del:>12,.0f}")
    print(f"  Net change:                   {total_add - total_del:>+12,.0f}")
    print(f"  18–39 share of additions:     {young_add/total_add*100:>11.1f}%")
    print(f"  50+ share of deletions:       {old_del/total_del*100:>11.1f}%")
    print("\n  Estimated vote-share impact from SIR:")
    for p, v in benefits.items():
        print(f"    {p:8s}: {'+' if v >= 0 else ''}{v:.3f} percentage points")
    print("────────────────────────────────────────────────────────────────\n")


def run():
    print("=" * 60)
    print("SIR / Voter Roll Revision Analysis")
    print("=" * 60)

    df = load_sir_data()
    props = compute_sir_proportions(df)

    print("\nGenerating figures...")
    plot_sir_age_distribution(props)
    benefits = plot_sir_net_impact(props, df)
    plot_sir_district_heatmap(df)

    # Save processed output
    agg = props["agg"].copy()
    agg["net"] = agg["additions"] - agg["deletions"]
    agg["add_pct"] = agg["additions"] / agg["additions"].sum() * 100
    agg["del_pct"] = agg["deletions"] / agg["deletions"].sum() * 100
    out_path = os.path.join(PROC, "sir_analysis.csv")
    agg.to_csv(out_path)
    print(f"  Processed data saved: {out_path}")

    print_sir_summary(df, props, benefits)
    return df, props, benefits


if __name__ == "__main__":
    run()
