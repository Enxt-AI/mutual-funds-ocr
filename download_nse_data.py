"""
Download NSE historical index data using yfinance.
Saves CSVs to nse_data/ directory.
"""

import os
import yfinance as yf
import pandas as pd
from datetime import datetime

# Output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "nse_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Index ticker mappings
# Yahoo Finance uses specific tickers for Indian indices
INDICES = {
    "NIFTY_50": "^NSEI",
    "NIFTY_NEXT_50": "^NSMIDCP50",  # Nifty Next 50
    "NIFTY_100": "^CNX100",
    "NIFTY_MIDCAP_150": "NIFTYMIDCAP150.NS",
    "NIFTY_SMALLCAP_250": "NIFTYSMLCAP250.NS",
    "NIFTY_500": "^CRSLDX",
    "NIFTY_BANK": "^NSEBANK",
    "SENSEX": "^BSESN",
    "NIFTY_IT": "^CNXIT",
    "NIFTY_FINANCIAL_SERVICES": "NIFTY_FIN_SERVICE.NS",
}

START_DATE = "2015-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")


def download_index(name: str, ticker: str) -> bool:
    """Download historical data for a single index."""
    try:
        print(f"  Downloading {name} ({ticker})...", end=" ")
        data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)

        if data.empty:
            print("NO DATA - ticker may be invalid")
            return False

        # Flatten multi-level columns if present (yfinance>=0.2.31)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Keep useful columns
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
        data = data[cols]
        data.index.name = "Date"

        # Save
        filepath = os.path.join(OUTPUT_DIR, f"{name}.csv")
        data.to_csv(filepath)
        print(f"OK - {len(data)} rows -> {filepath}")
        return True

    except Exception as e:
        print(f"FAILED - {e}")
        return False


def main():
    print(f"Downloading NSE index data ({START_DATE} to {END_DATE})")
    print(f"Output directory: {OUTPUT_DIR}\n")

    results = {}
    for name, ticker in INDICES.items():
        results[name] = download_index(name, ticker)

    # Summary
    print("\n" + "=" * 50)
    print("DOWNLOAD SUMMARY")
    print("=" * 50)
    success = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    print(f"Success: {success}/{len(results)}")
    if failed:
        print(f"Failed:  {', '.join(k for k, v in results.items() if not v)}")

    # List saved files
    print(f"\nSaved files in {OUTPUT_DIR}/:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.endswith(".csv"):
            size = os.path.getsize(os.path.join(OUTPUT_DIR, f))
            print(f"  {f} ({size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
