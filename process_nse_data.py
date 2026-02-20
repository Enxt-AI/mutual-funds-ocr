"""
Process NSE Index CSVs into a unified JSON for the frontend.
Outputs to: website/app/data/indices.json
"""

import os
import json
import pandas as pd
from pathlib import Path

# Mapping filename/ticker to friendly ID
INDEX_MAP = {
    "NIFTY_50": "nifty-50",
    "NIFTY_NEXT_50": "nifty-next-50",
    "NIFTY_100": "nifty-100",
    "NIFTY_500": "nifty-500",
    "NIFTY_MIDCAP_150": "nifty-midcap-150",
    "NIFTY_SMALLCAP_250": "nifty-smallcap-250",
    "NIFTY_BANK": "nifty-bank",
    "NIFTY_IT": "nifty-it",
    "NIFTY_FINANCIAL_SERVICES": "nifty-financial-services",
    "SENSEX": "sensex",
}

def process_indices():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "nse_data"
    output_path = base_dir / "website" / "app" / "data" / "indices.json"
    
    output_data = {}
    
    csv_files = list(data_dir.glob("*.csv"))
    
    
    for csv_file in csv_files:
        # Identify index
        file_stem = csv_file.stem
        # Sort keys by length descending to avoid substring matches (e.g. 50 matching 500)
        sorted_keys = sorted(INDEX_MAP.keys(), key=len, reverse=True)
        
        index_key = None
        for key in sorted_keys:
            if file_stem.startswith(key):
                index_key = INDEX_MAP[key]
                break
        
        if not index_key:
            print(f"Skipping unknown file: {csv_file.name}")
            continue
            
        print(f"Processing {index_key}...", end=" ")
        
        try:
            df = pd.read_csv(csv_file)
            
            # Ensure Date and Close exist
            if "Date" not in df.columns or "Close" not in df.columns:
                print(f"FAILED - Missing columns. Found: {df.columns}")
                continue
            
            # Sort by date
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date")
            
            # Extract data points
            points = []
            for _, row in df.iterrows():
                points.append({
                    "date": row["Date"].strftime("%Y-%m-%d"),
                    "val": round(float(row["Close"]), 2)
                })
            
            output_data[index_key] = points
            print(f"OK ({len(points)} points)")
            
        except Exception as e:
            print(f"ERROR: {e}")

    # Save to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, separators=(',', ':'))  # Minified
        
    

if __name__ == "__main__":
    process_indices()
