"""Get full factsheet details from Bandhan MF WordPress API."""
import requests
import json

headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://bandhanmutual.com",
    "Referer": "https://bandhanmutual.com/",
}

url = "https://cmsnew.bandhanmutual.com/wp-json/finance-api/v1/posts/monthly-factsheets?bypass_pagination=true"
print(f"Fetching: {url}")
resp = requests.get(url, headers=headers, timeout=15)
data = resp.json()

print(f"Status: {data.get('status')}")
print(f"Data items: {len(data.get('data', []))}")

# Show choices
print(f"\n=== Choices ===")
choices = data.get('choices', [])
if isinstance(choices, list):
    for c in choices[:10]:
        print(f"  {c}")
elif isinstance(choices, dict):
    print(json.dumps(choices, indent=2)[:1000])

# Show first 3 data items in full
print(f"\n=== First 3 data items ===")
items = data.get('data', [])
for i, item in enumerate(items[:3]):
    print(f"\n--- Item {i+1} ---")
    print(json.dumps(item, indent=2)[:1500])

# Find items with factsheet PDF
print(f"\n=== All items with titles ===")
for item in items:
    title = item.get('title', '')
    acf = item.get('acf_fields', {})
    # Look for any field that might contain a PDF URL
    pdf_fields = {}
    for k, v in acf.items():
        if isinstance(v, str) and ('.pdf' in v.lower() or 'http' in v.lower()):
            pdf_fields[k] = v
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, str) and '.pdf' in v2.lower():
                    pdf_fields[f"{k}.{k2}"] = v2
    
    fy = acf.get('financial_year', '')
    month = acf.get('month', '') or acf.get('factsheet_month', '')
    
    print(f"  {title} | FY: {fy} | Month: {month}")
    if pdf_fields:
        for k, v in pdf_fields.items():
            print(f"    PDF: {k} = {v[:200]}")
