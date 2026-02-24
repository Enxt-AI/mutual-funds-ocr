"""Quick probe for Angel One factsheet PDF links."""
import requests
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

url = "https://www.angelonemf.com/downloads"
resp = requests.get(url, headers=headers, timeout=15)
print(f"Status: {resp.status_code}, Length: {len(resp.text)}")

# Find ALL PDF links
pdf_links = re.findall(r'href=["\']([^"\']*\.pdf)["\']', resp.text, re.IGNORECASE)
print(f"\nTotal PDF links: {len(pdf_links)}")

# Filter for factsheet-related
factsheet_links = [l for l in pdf_links if 'factsheet' in l.lower() or 'fact-sheet' in l.lower()]
print(f"Factsheet PDFs: {len(factsheet_links)}")
for link in factsheet_links:
    print(f"  {link}")

# Look for API endpoints
api_matches = re.findall(r'["\']([^"\']*(?:api|graphql|wp-json)[^"\']*)["\']', resp.text, re.IGNORECASE)
print(f"\nAPI endpoints found: {len(api_matches)}")
for api in set(api_matches)[:10]:
    print(f"  {api}")

# Look for any "factsheet" mentions in the HTML
factsheet_mentions = [(m.start(), resp.text[max(0,m.start()-50):m.end()+100]) for m in re.finditer(r'factsheet', resp.text, re.IGNORECASE)]
print(f"\n'factsheet' mentions in HTML: {len(factsheet_mentions)}")
for pos, context in factsheet_mentions[:10]:
    clean = context.replace('\n', ' ').strip()
    print(f"  @{pos}: ...{clean}...")
