"""
01_collect_eci_data.py
======================
Downloads TN election results from ECI website for 2026 and historical
elections (2001, 2006, 2011, 2016, 2021).

Run this FIRST before any notebook analysis.
Outputs saved to ../data/raw/
"""

import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ── ECI 2026 results (live / recently published) ───────────────────────────
# ECI publishes constituency-wise results at:
# https://results.eci.gov.in/  (for the current election cycle)
# The direct AC-wise result table URL format for Tamil Nadu (state code 11):
ECI_2026_BASE = "https://results.eci.gov.in/ResultAcGenMay2026/partywiseresult-S11.htm"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_2026_party_summary() -> pd.DataFrame:
    """Scrape party-wise seat summary for TN 2026 from ECI results portal."""
    print("Fetching 2026 party-wise summary...")
    try:
        r = requests.get(ECI_2026_BASE, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        tables = pd.read_html(r.text)
        if tables:
            df = tables[0]
            df.to_csv(os.path.join(RAW_DIR, "tn2026_party_summary.csv"), index=False)
            print(f"  Saved {len(df)} rows → tn2026_party_summary.csv")
            return df
    except Exception as e:
        print(f"  [WARN] Could not auto-fetch 2026 summary: {e}")
        print("  → Please manually download the ECI result table and save to:")
        print(f"    {RAW_DIR}/tn2026_party_summary.csv")
    return pd.DataFrame()


def fetch_2026_constituency_results() -> pd.DataFrame:
    """
    Attempt to scrape all 234 AC results from ECI.
    ECI URL pattern: /ResultAcGenMay2026/constituencywise-S11<AC_NO>.htm
    AC numbers for TN: 1 to 234
    """
    print("\nFetching 2026 constituency-wise results (234 ACs)...")
    all_rows = []
    consecutive_failures = 0
    FAST_FAIL_THRESHOLD = 5  # abort if first 5 ACs all fail (site is blocking)

    for ac_no in range(1, 235):
        url = (
            f"https://results.eci.gov.in/ResultAcGenMay2026/"
            f"constituencywise-S11{ac_no:03d}.htm"
        )
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            tables = pd.read_html(r.text)
            if tables:
                df = tables[0].copy()
                df["AC_NO"] = ac_no
                all_rows.append(df)
                consecutive_failures = 0
                print(f"  AC {ac_no:3d}/234 ✓", end="\r")
        except Exception:
            consecutive_failures += 1
            print(f"  AC {ac_no:3d}/234 ✗ (skipped)")
            if ac_no <= FAST_FAIL_THRESHOLD and consecutive_failures >= FAST_FAIL_THRESHOLD:
                print(f"\n  [ABORT] First {FAST_FAIL_THRESHOLD} ACs all failed — ECI is blocking scraping.")
                print("  → Download results manually from https://results.eci.gov.in/")
                print(f"    Save as: {RAW_DIR}/tn2026_constituency_results.csv")
                break
        time.sleep(0.3)

    if all_rows:
        result = pd.concat(all_rows, ignore_index=True)
        result.to_csv(
            os.path.join(RAW_DIR, "tn2026_constituency_results.csv"), index=False
        )
        print(f"\n  Saved {len(result)} rows → tn2026_constituency_results.csv")
        return result
    else:
        print("\n  [WARN] No data fetched. Download manually from ECI and place in data/raw/")
        return pd.DataFrame()


# ── Historical data via TCPD Lok Dhaba ─────────────────────────────────────
# Trivedi Centre for Political Data: https://tcpd.ashoka.edu.in/lok-dhaba/
# They provide downloadable CSV exports for state assembly elections.
# Manual download instructions (free, no login required):
TCPD_INSTRUCTIONS = """
TCPD Historical Data (2001-2021):
──────────────────────────────────
1. Go to: https://tcpd.ashoka.edu.in/lok-dhaba/
2. Select: "Vidhan Sabha (State Elections)"
3. State: Tamil Nadu
4. Years: 2001, 2006, 2011, 2016, 2021  (download each separately)
5. Click "Download CSV"
6. Save files as:
     data/raw/tn_results_2001.csv
     data/raw/tn_results_2006.csv
     data/raw/tn_results_2011.csv
     data/raw/tn_results_2016.csv
     data/raw/tn_results_2021.csv
"""

# ── EC Cash Seizure Data ────────────────────────────────────────────────────
EC_SEIZURE_INSTRUCTIONS = """
EC Cash/Liquor/Drug Seizure Data:
───────────────────────────────────
1. SUVIDHA portal (ECI): https://suvidha.eci.gov.in/
2. cVIGIL complaint statistics by district
3. Also check: https://eci.gov.in/mcc/ (MCC enforcement data per state)
4. Press releases from CEO Tamil Nadu: https://www.elections.tn.gov.in/
   → Save seizure tables as:  data/raw/tn_cash_seizures_2026.csv
   → Columns expected: district, cash_INR_cr, liquor_liters, freebies_INR_cr, date

Alternative: ADR (Association for Democratic Reforms)
   https://adrindia.org/  → Tamil Nadu Election Watch data
"""


def print_manual_instructions():
    print(TCPD_INSTRUCTIONS)
    print(EC_SEIZURE_INSTRUCTIONS)


if __name__ == "__main__":
    print("=" * 60)
    print("TN Election Data Collection")
    print("=" * 60)
    fetch_2026_party_summary()
    fetch_2026_constituency_results()
    print_manual_instructions()
    print("\nDone. Check data/raw/ for downloaded files.")
