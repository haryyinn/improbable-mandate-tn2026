"""
run_all.py
==========
Master script — runs the full pipeline in order and generates the paper.

Usage
-----
    python3 run_all.py

Before running, make sure you have placed the following files in data/raw/:
  - tn_results_2001.csv ... tn_results_2021.csv  (from TCPD Lok Dhaba)
  - tn2026_constituency_results.csv               (from ECI / auto-fetched)
  - tn_sir_2026.csv                               (from CEO Tamil Nadu)
  - tn_cash_seizures_2026.csv                     (from CEO Tamil Nadu / ADR)

The script will generate synthetic/placeholder data for any missing files
so the paper always compiles. Replace with real data for final results.

Update the ACTUALS section below when you know the final seat counts.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

# ── Actual results from ECI (results.eci.gov.in/ResultAcGenMay2026/) ──────
# Source: tn2026_party_summary.csv parsed from official ECI webarchive
ACTUAL_TVK_SEATS  = 108
ACTUAL_DMK_SEATS  = 59
ACTUAL_ADMK_SEATS = 47
# ───────────────────────────────────────────────────────────────────────────

def step(n: int, label: str):
    print(f"\n{'='*60}")
    print(f"  STEP {n}: {label}")
    print(f"{'='*60}")


if __name__ == "__main__":

    step(0, "Parse ECI webarchives (fallback / partial-page data)")
    import importlib
    parser = importlib.import_module("00_parse_webarchives")
    parser.run()

    step(0.5, "Load official ECI Excel (authoritative; overrides webarchive)")
    excel_loader = importlib.import_module("00_load_eci_excel")
    excel_loader.run()

    step(1, "Data Collection — ECI Scrape + Manual Source Guidance")
    import importlib
    collect = importlib.import_module("01_collect_eci_data")
    collect.fetch_2026_party_summary()
    collect.fetch_2026_constituency_results()
    collect.print_manual_instructions()

    step(2, "Data Cleaning & Merging")
    clean = importlib.import_module("02_clean_and_merge")
    clean  # module-level code runs on import; call main if needed

    step(3, "SIR Voter Roll Revision Analysis")
    sir = importlib.import_module("03_sir_analysis")
    sir.run()

    step(4, "Historical Trend Analysis")
    hist = importlib.import_module("04_historical_analysis")
    hist.run()

    step(5, "Monte Carlo Simulation")
    mc = importlib.import_module("05_monte_carlo")
    mc.run(actual_tvk_seats=ACTUAL_TVK_SEATS)

    step(6, "Bribe / Cash Seizure Analysis")
    bribe = importlib.import_module("06_bribe_analysis")
    bribe.run()

    step(7, "Generating Research Paper (.docx)")
    paper = importlib.import_module("07_generate_paper")
    out_docx = paper.build_paper(
        actual_tvk_seats=ACTUAL_TVK_SEATS,
        actual_dmk_seats=ACTUAL_DMK_SEATS,
        actual_admk_seats=ACTUAL_ADMK_SEATS,
    )

    step(8, "Generating Interactive HTML Companion")
    html_gen = importlib.import_module("08_generate_interactive_html")
    out_html = html_gen.run({
        "TVK": ACTUAL_TVK_SEATS,
        "DMK": ACTUAL_DMK_SEATS,
        "ADMK": ACTUAL_ADMK_SEATS,
    })

    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"  Word paper:   {out_docx}")
    print(f"  Interactive:  {out_html}")
    print(f"{'='*60}\n")
