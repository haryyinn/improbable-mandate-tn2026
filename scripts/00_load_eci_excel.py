"""
00_load_eci_excel.py
====================
Loads the official ECI Tamil Nadu 2026 results Excel (compiled from
results.eci.gov.in) and writes canonical CSVs that downstream scripts
consume.

Expected input (place in data/raw/):
    eci_tamil_nadu_results_may_2026.xlsx

The workbook has four sheets:
    Summary       — metadata
    Party Summary — 12 parties × {Code, Name, Seats, Votes, Margins}
    Winners       — 234 rows × {AC No., Constituency, Party, Candidate,
                                 Total Votes (= winning candidate votes),
                                 Margin, Round Status, Source URL}
    Sources       — primary URL list

Outputs (data/raw/):
    tn2026_party_summary.csv          — full official party totals
    tn2026_constituency_results.csv   — 234 winners with cleaned columns
    tn2026_summary_2026.csv           — schema-compatible with the
                                         downstream tn_elections_summary.csv
                                         (year, ac_no, ac_name, winner_party,
                                          winner_votes, runner_votes,
                                          total_votes, margin, margin_pct,
                                          winner_vote_share, n_candidates)
    eci_sources.csv                   — primary source URLs
"""

import os
import warnings
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW  = os.path.join(ROOT, "data", "raw")

EXCEL = os.path.join(RAW, "eci_tamil_nadu_results_may_2026.xlsx")

# Map ECI party codes to canonical groupings used downstream
PARTY_GROUP = {
    "TVK":      "TVK",
    "DMK":      "DMK",
    "ADMK":     "ADMK",
    "AIADMK":   "ADMK",
    "INC":      "INC",
    "BJP":      "BJP",
    "PMK":      "OTHERS",
    "CPI":      "OTHERS",
    "CPI(M)":   "OTHERS",
    "IUML":     "OTHERS",
    "VCK":      "OTHERS",
    "DMDK":     "OTHERS",
    "AMMKMNKZ": "OTHERS",
    "MNM":      "OTHERS",
    "NTK":      "OTHERS",
}


def map_party(code: str) -> str:
    """Map ECI party code → canonical group for downstream analysis."""
    if not isinstance(code, str):
        return "OTHERS"
    code = code.strip().upper()
    return PARTY_GROUP.get(code, "OTHERS")


def load_party_summary(xl: pd.ExcelFile) -> pd.DataFrame:
    df = xl.parse("Party Summary").copy()
    df.columns = [c.strip() for c in df.columns]
    # Coerce numeric columns
    numeric_cols = ["Seats Won", "Winning Candidate Votes", "Avg Winning Votes",
                    "Min Margin", "Max Margin", "Avg Margin"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Party Code"]).reset_index(drop=True)
    return df


def load_winners(xl: pd.ExcelFile) -> pd.DataFrame:
    df = xl.parse("Winners").copy()
    df.columns = [c.strip() for c in df.columns]
    # Coerce numerics
    df["AC No."]      = pd.to_numeric(df["AC No."],      errors="coerce")
    df["Total Votes"] = pd.to_numeric(df["Total Votes"], errors="coerce")
    df["Margin"]      = pd.to_numeric(df["Margin"],      errors="coerce")
    df = df.dropna(subset=["AC No.", "Total Votes", "Margin"]).reset_index(drop=True)
    df["AC No."]      = df["AC No."].astype(int)
    df["Total Votes"] = df["Total Votes"].astype(int)
    df["Margin"]      = df["Margin"].astype(int)
    return df


def load_sources(xl: pd.ExcelFile) -> pd.DataFrame:
    df = xl.parse("Sources").copy()
    df.columns = [c.strip() for c in df.columns]
    return df


def winners_to_summary_schema(winners: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the official Winners table to the schema downstream scripts
    expect (matching synthesize_summary_from_aggregates()).

    Note: ECI publishes only the winning candidate's vote count, not the
    full constituency turnout. We approximate total_votes by assuming the
    top-two candidates capture ~85% of votes cast — a defensible Tamil Nadu
    average. This affects margin_pct and winner_vote_share but not winner
    identity, margin (absolute), or seat counts.
    """
    rows = []
    for _, w in winners.iterrows():
        winner_votes = int(w["Total Votes"])
        margin       = int(w["Margin"])
        runner_votes = max(0, winner_votes - margin)
        # Approximate total cast: top-two ≈ 85% of valid votes
        total_votes  = int(round((winner_votes + runner_votes) / 0.85))
        margin_pct   = round(100.0 * margin / total_votes, 2) if total_votes else 0.0
        winner_share = round(100.0 * winner_votes / total_votes, 2) if total_votes else 0.0

        rows.append({
            "year":              2026,
            "ac_no":             int(w["AC No."]),
            "ac_name":           str(w["Constituency"]).strip(),
            "winner_party":      map_party(w["Party Code"]),
            "winner_party_full": str(w["Party Name"]).strip(),
            "winner_party_code": str(w["Party Code"]).strip(),
            "winner_candidate":  str(w["Winning Candidate"]).strip(),
            "winner_votes":      winner_votes,
            "runner_votes":      runner_votes,
            "total_votes":       total_votes,
            "margin":            margin,
            "margin_pct":        margin_pct,
            "winner_vote_share": winner_share,
            "n_candidates":      0,  # not in this dataset; downstream uses it loosely
            "source_url":        str(w.get("Source URL", "")).strip(),
        })
    return pd.DataFrame(rows)


def run():
    print("=" * 60)
    print("Loading official ECI Excel")
    print("=" * 60)

    if not os.path.exists(EXCEL):
        print(f"  [SKIP] Excel not found at {EXCEL}")
        return

    print(f"  Reading {EXCEL}")
    xl = pd.ExcelFile(EXCEL)
    print(f"  Sheets: {xl.sheet_names}")

    # 1. Party summary
    party = load_party_summary(xl)
    out_party = os.path.join(RAW, "tn2026_party_summary.csv")
    party.to_csv(out_party, index=False)
    print(f"\n  [1/3] Party summary → {len(party)} parties saved to:")
    print(f"        {out_party}")
    print(party[["Party Code", "Seats Won", "Winning Candidate Votes",
                 "Avg Margin"]].to_string(index=False))

    # 2. Winners → constituency CSV (cleaned, with extra metadata)
    winners = load_winners(xl)
    out_const = os.path.join(RAW, "tn2026_constituency_results.csv")
    winners.to_csv(out_const, index=False)
    print(f"\n  [2/3] Winners → {len(winners)} constituencies saved to:")
    print(f"        {out_const}")
    seat_counts = (winners.groupby("Party Code").size()
                          .sort_values(ascending=False))
    print("        Seat tally (top 8):")
    for p, n in seat_counts.head(8).items():
        print(f"          {p:<10s} {n:>4d}")

    # 3. Schema-compatible summary for downstream scripts
    summary_2026 = winners_to_summary_schema(winners)
    out_summary  = os.path.join(RAW, "tn2026_summary_2026.csv")
    summary_2026.to_csv(out_summary, index=False)
    print(f"\n  [3/3] Downstream-schema summary saved to:")
    print(f"        {out_summary}")

    # 4. Sources sheet
    if "Sources" in xl.sheet_names:
        sources = load_sources(xl)
        out_src = os.path.join(RAW, "eci_sources.csv")
        sources.to_csv(out_src, index=False)
        print(f"\n  [bonus] Source URL list saved to:")
        print(f"          {out_src}")

    print("\n  Done.")


if __name__ == "__main__":
    run()
