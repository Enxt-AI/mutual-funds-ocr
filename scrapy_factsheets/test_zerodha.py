"""List all Zerodha Fund House report categories and find factsheets."""
import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

r = requests.get("https://api.zerodhafundhouse.com/api/v1/reports", headers=headers, timeout=10)
data = r.json()
items = data.get("data", [])

print(f"Total categories: {len(items)}\n")

for item in items:
    cat_id = item.get("id", "?")
    title = item.get("title", "?")
    files = item.get("files", [])
    print(f"  [{cat_id}] {title} ({len(files)} files)")
    
    # Check if any file has "factsheet" in name
    for f in files:
        name = f.get("name", "").lower()
        if "factsheet" in name:
            print(f"    *** FACTSHEET: {f.get('name')}")
            print(f"        URL: {f.get('url')}")
            print(f"        Date: {f.get('modTs')}")
