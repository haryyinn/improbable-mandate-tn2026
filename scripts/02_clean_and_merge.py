"""
02_clean_and_merge.py
======================
Cleans raw CSVs and produces a unified historical DataFrame
spanning TN assembly elections 2001-2026.

Output: data/processed/tn_elections_combined.csv
        data/processed/tn2026_clean.csv
"""

import os
import pandas as pd
import numpy as np

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROC = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(PROC, exist_ok=True)

YEARS = [2001, 2006, 2011, 2016, 2021]

# Column name mapping to standardise across TCPD CSVs
TCPD_COL_MAP = {
    "Constituency_No": "ac_no",
    "Constituency_Name": "ac_name",
    "Party": "party",
    "Candidate": "candidate",
    "Votes": "votes",
    "Position": "position",
    "Year": "year",
    "State_Name": "state",
    "Total_Votes": "total_votes",
    "Turnout_Percentage": "turnout_pct",
    "Vote_Share_Percentage": "vote_share_pct",
}


def load_tcpd_year(year: int) -> pd.DataFrame:
    path = os.path.join(RAW, f"tn_results_{year}.csv")
    if not os.path.exists(path):
        print(f"  [SKIP] {path} not found.")
        return pd.DataFrame()
    df = pd.read_csv(path)
    df = df.rename(columns=TCPD_COL_MAP)
    df["year"] = year
    return df


def load_2026() -> pd.DataFrame:
    path = os.path.join(RAW, "tn2026_constituency_results.csv")
    if not os.path.exists(path):
        print("  [SKIP] tn2026_constituency_results.csv not found.")
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["year"] = 2026
    return df


def compute_winner_margin(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each (year, ac_no) compute:
      winner_votes, runner_votes, margin, margin_pct, winner_party
    """
    results = []
    for (year, ac), grp in df.groupby(["year", "ac_no"]):
        grp = grp.sort_values("votes", ascending=False).reset_index(drop=True)
        if len(grp) < 2:
            continue
        winner = grp.iloc[0]
        runner = grp.iloc[1]
        results.append(
            {
                "year": year,
                "ac_no": ac,
                "ac_name": winner.get("ac_name", ""),
                "winner": winner.get("candidate", ""),
                "winner_party": winner.get("party", ""),
                "winner_votes": winner["votes"],
                "runner_party": runner.get("party", ""),
                "runner_votes": runner["votes"],
                "total_votes": grp["votes"].sum(),
                "margin": winner["votes"] - runner["votes"],
                "margin_pct": round(
                    (winner["votes"] - runner["votes"]) / grp["votes"].sum() * 100, 2
                ),
                "winner_vote_share": round(
                    winner["votes"] / grp["votes"].sum() * 100, 2
                ),
                "n_candidates": len(grp),
            }
        )
    return pd.DataFrame(results)


if __name__ == "__main__":
    print("Loading historical TCPD data...")
    frames = [load_tcpd_year(y) for y in YEARS]
    frames = [f for f in frames if not f.empty]

    print("Loading 2026 data...")
    df26 = load_2026()
    if not df26.empty:
        frames.append(df26)

    if not frames:
        print("No data loaded. Run 01_collect_eci_data.py first.")
    else:
        combined = pd.concat(frames, ignore_index=True)
        combined.to_csv(os.path.join(PROC, "tn_elections_combined.csv"), index=False)
        print(f"Combined dataset: {len(combined)} rows → tn_elections_combined.csv")

        summary = compute_winner_margin(combined)
        summary.to_csv(os.path.join(PROC, "tn_elections_summary.csv"), index=False)
        print(f"Winner-margin summary: {len(summary)} rows → tn_elections_summary.csv")
