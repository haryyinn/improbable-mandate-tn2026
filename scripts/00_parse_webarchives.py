"""
00_parse_webarchives.py
=======================
Parses Safari .webarchive files saved from the ECI results portal and
extracts the underlying tables into clean CSV files.

Inputs (place in data/raw/):
  - eci_partywise.webarchive       (party-wise totals page)
  - eci_constituency.webarchive    (constituency-wise list page)

Outputs:
  - data/raw/tn2026_party_summary.csv
  - data/raw/tn2026_constituency_results.csv

Run this BEFORE 01_collect_eci_data.py if you have webarchives.
The downstream scripts will detect the CSVs automatically and use real
data instead of synthetic placeholders.
"""

import os
import re
import plistlib
import pandas as pd
from io import StringIO

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW  = os.path.join(ROOT, "data", "raw")


def load_html_from_webarchive(path: str) -> str:
    """Safari .webarchive is a binary plist. The HTML lives at
    WebMainResource → WebResourceData."""
    with open(path, "rb") as f:
        archive = plistlib.load(f)
    html = archive["WebMainResource"]["WebResourceData"]
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")
    return html


def extract_all_tables(html: str) -> list:
    """Use pandas.read_html to pull every table, then return non-empty ones."""
    try:
        tables = pd.read_html(StringIO(html))
    except ValueError:
        return []
    # Filter out empty / single-cell tables
    return [t for t in tables if t.shape[0] >= 2 and t.shape[1] >= 2]


def parse_partywise(html: str) -> pd.DataFrame:
    """
    The party-wise page typically has one large table with columns like:
      Party | Won | Leading | Total
    """
    tables = extract_all_tables(html)
    print(f"  Party-wise: found {len(tables)} candidate tables")

    # Find the table that has 'Won' and 'Party' (or similar) columns
    for i, t in enumerate(tables):
        cols = [str(c).strip().lower() for c in t.columns]
        cols_str = " ".join(cols)
        if ("won" in cols_str and ("party" in cols_str or "leading" in cols_str)):
            print(f"  → using table #{i} with columns: {list(t.columns)}")
            return t

    # Fallback: pick the table with "Total" row
    for i, t in enumerate(tables):
        first_col = t.iloc[:, 0].astype(str).str.lower()
        if first_col.str.contains("total", na=False).any() and t.shape[1] >= 3:
            print(f"  → fallback: table #{i}")
            return t

    print("  [WARN] Could not locate party-wise table.")
    return pd.DataFrame()


def parse_constituency(html: str) -> pd.DataFrame:
    """
    The constituency page typically lists every AC with columns like:
      Constituency | Const. No. | Leading Candidate | Leading Party |
      Trailing Candidate | Trailing Party | Margin | Round | Status
    """
    tables = extract_all_tables(html)
    print(f"  Constituency: found {len(tables)} candidate tables")

    # Look for the table that contains many rows with "Result Declared"
    # OR has "Leading Party" / "Margin" in columns
    best = None
    best_score = 0
    for i, t in enumerate(tables):
        cols_lower = " ".join(str(c).lower() for c in t.columns)
        body_lower = t.astype(str).apply(lambda c: c.str.lower()).values.flatten()
        body_text = " ".join(body_lower)

        score = 0
        if "leading" in cols_lower or "trailing" in cols_lower:
            score += 5
        if "margin" in cols_lower:
            score += 3
        if "constituency" in cols_lower or "const" in cols_lower:
            score += 2
        if "result declared" in body_text:
            score += min(t.shape[0] / 10, 5)  # cap at 5
        if t.shape[0] >= 20:  # constituency lists are long
            score += 2

        if score > best_score:
            best_score = score
            best = (i, t)

    if best:
        i, t = best
        print(f"  → chose table #{i} (score={best_score:.1f}, "
              f"rows={t.shape[0]}, cols={list(t.columns)})")
        return t

    print("  [WARN] Could not locate constituency table.")
    return pd.DataFrame()


def clean_partywise(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    # Drop any 'Total' row
    first_col = df.columns[0]
    df = df[~df[first_col].astype(str).str.lower().str.contains("total", na=False)]
    # Coerce numeric columns
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="ignore")
    df.reset_index(drop=True, inplace=True)
    return df


def clean_constituency(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()

    # 1. Flatten multi-index column headers from ECI tables
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[-1] if isinstance(c, tuple) else c for c in df.columns]
    df.columns = [str(c).strip() for c in df.columns]

    # 2. Strip whitespace in every cell
    for c in df.columns:
        if df[c].dtype == "object":
            df[c] = df[c].astype(str).str.strip()

    # 3. Drop rows where Const. No. isn't numeric (these are the
    #    interleaved "Won In: 108", "Trailing In: 0" metadata rows)
    if "Const. No." in df.columns:
        df["Const. No."] = pd.to_numeric(df["Const. No."], errors="coerce")
        df = df.dropna(subset=["Const. No."]).reset_index(drop=True)
        df["Const. No."] = df["Const. No."].astype(int)

    # 4. Strip the "iParty Wise State Trends..." junk that ECI appends
    #    to party names in the rendered HTML
    junk_re = re.compile(r"\s*i?Party Wise State Trends.*$", re.IGNORECASE)
    for col in ("Leading Party", "Trailing Party"):
        if col in df.columns:
            df[col] = df[col].astype(str).apply(lambda s: junk_re.sub("", s).strip())

    # 5. Coerce Margin to integer where possible
    if "Margin" in df.columns:
        df["Margin"] = pd.to_numeric(
            df["Margin"].astype(str).str.replace(",", "").str.replace(".0", "", regex=False),
            errors="coerce"
        ).fillna(0).astype(int)

    return df


def run():
    print("=" * 60)
    print("Parsing ECI webarchives")
    print("=" * 60)

    party_path = os.path.join(RAW, "eci_partywise.webarchive")
    cons_path  = os.path.join(RAW, "eci_constituency.webarchive")

    if os.path.exists(party_path):
        print(f"\n[1/2] Reading {party_path}")
        html = load_html_from_webarchive(party_path)
        df = clean_partywise(parse_partywise(html))
        if not df.empty:
            out = os.path.join(RAW, "tn2026_party_summary.csv")
            df.to_csv(out, index=False)
            print(f"  Saved {len(df)} rows → {out}")
            print(df.head(15).to_string(index=False))
        else:
            print("  [WARN] No party-wise data extracted.")
    else:
        print(f"\n[1/2] Skipping — {party_path} not found")

    if os.path.exists(cons_path):
        print(f"\n[2/2] Reading {cons_path}")
        html = load_html_from_webarchive(cons_path)
        df = clean_constituency(parse_constituency(html))
        if not df.empty:
            out = os.path.join(RAW, "tn2026_constituency_results.csv")
            df.to_csv(out, index=False)
            print(f"  Saved {len(df)} rows → {out}")
            print(df.head(8).to_string(index=False))
        else:
            print("  [WARN] No constituency data extracted.")
    else:
        print(f"\n[2/2] Skipping — {cons_path} not found")

    print("\nDone.")


if __name__ == "__main__":
    run()
