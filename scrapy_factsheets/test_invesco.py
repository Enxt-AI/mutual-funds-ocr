"""Extract factsheet structure from Invesco API."""
import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://invescomutualfund.com/literature-and-form?tab=Factsheets",
}

# Use www prefix to avoid DNS issue
url = "https://www.invescomutualfund.com/api/RequestForLiterature?year=0"
print(f"Fetching {url}...")
r = requests.get(url, headers=headers, timeout=15)
print(f"Status: {r.status_code}, {len(r.text)} chars")

data = r.json()
print(f"Type: list[{len(data)}]")
print(f"Keys: {list(data[0].keys())}")

# Focus on Factsheet key
factsheets = data[0].get('Factsheet', [])
print(f"\nFactsheet entries: {len(factsheets)}")
for i, fs in enumerate(factsheets[:5]):
    print(f"\n  [{i}] {json.dumps(fs)[:400]}")

# Show all factsheet items with their dates and URLs
print("\n\n=== All factsheet items ===")
for fs in factsheets:
    if isinstance(fs, dict):
        name = fs.get('DocumentName', fs.get('FactsheetName', ''))
        url = fs.get('DocumentUrl', fs.get('FactsheetUrl', ''))
        date = fs.get('DocumentDate', fs.get('FactsheetDate', ''))
        year = fs.get('Year', '')
        print(f"  {name[:60]} | {date} | Year={year}")
        print(f"    URL: {url[:150]}")
