"""Dump UTI MF component [12] full structure and test month formats."""
import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Get full component [12]
r = requests.get("https://www.utimf.com/api/page/forms-and-downloads-downloads", headers=headers, timeout=15)
data = r.json()
comp = data["field_component"][12]
print("=== Component [12] full dump ===")
print(json.dumps(comp, indent=2)[:3000])

# Test different month formats
base = "https://www.utimf.com/api/get-fact-sheet"
for year, month in [
    ("2026", "January"), ("2026", "january"), ("2026", "Jan"),
    ("2025", "December"), ("2025", "december"), ("2025", "Dec"),
    ("2026", "1"), ("2025", "12"),
    ("2026-01", ""), ("2025-12", ""),
]:
    if month:
        url = f"{base}?year={year}&month={month}"
    else:
        url = f"{base}?year={year}"
    r2 = requests.get(url, headers=headers, timeout=5)
    try:
        d = r2.json()
        rows = d.get("rows", [])
        if rows:
            print(f"\n*** FOUND: year={year}&month={month}: {len(rows)} rows ***")
            print(f"  First: {json.dumps(rows[0])[:500]}")
        else:
            pass  # Skip empty
    except:
        if r2.status_code != 200 or len(r2.text) > 50:
            print(f"year={year}&month={month}: {r2.status_code}, {r2.text[:200]}")

# Also try POST
for year, month in [("2026", "January"), ("2026", "01")]:
    r3 = requests.post(base, headers={**headers, "Content-Type": "application/json"},
                       json={"year": year, "month": month}, timeout=5)
    try:
        d = r3.json()
        rows = d.get("rows", [])
        if rows:
            print(f"\nPOST year={year}&month={month}: {len(rows)} rows")
            print(f"  {json.dumps(rows[0])[:500]}")
    except:
        print(f"POST year={year}&month={month}: {r3.status_code}, {r3.text[:200]}")

# Check other similar endpoints from the components
for i, comp in enumerate(data["field_component"]):
    if isinstance(comp, dict) and "document_filter_api" in comp:
        api = comp["document_filter_api"]
        label = comp.get("document_category_label", "")
        print(f"\n  [{i}] {label}: {api}")
