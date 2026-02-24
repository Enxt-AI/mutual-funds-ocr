"""Analyze Canara Robeco factsheet page structure."""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

url = "https://www.canararobeco.com/documents/forms-downloads/forms-information-documents/information-documents/factsheets/"
print(f"Fetching: {url}")
resp = requests.get(url, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type')}")
print(f"Content length: {len(resp.text)} chars")

text = resp.text

# Check if SPA
is_spa = any(k in text.lower() for k in ['ng-app', 'react-root', '__next', '<div id="root"', '<div id="app"'])
print(f"Appears to be SPA: {is_spa}")

# Find all PDF links
pdf_links = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', text, re.IGNORECASE)
print(f"\nPDF links found: {len(pdf_links)}")
for p in list(set(pdf_links))[:15]:
    print(f"  {p}")

# Find download/factsheet links
download_links = re.findall(r'href=["\']([^"\']*(?:download|factsheet)[^"\']*)["\']', text, re.IGNORECASE)
print(f"\nDownload/Factsheet links: {len(download_links)}")
for d in list(set(download_links))[:15]:
    print(f"  {d}")

# Find API patterns
api_patterns = re.findall(r'["\']([^"\']*api[^"\']*)["\']', text, re.IGNORECASE)
relevant_api = [a for a in api_patterns if 'factsheet' in a.lower() or 'download' in a.lower()]
print(f"\nRelevant API patterns: {len(relevant_api)}")
for a in relevant_api[:10]:
    print(f"  {a}")

# Parse with BeautifulSoup
try:
    soup = BeautifulSoup(text, 'html.parser')
    
    # Find download anchors
    download_anchors = soup.find_all('a', href=re.compile(r'\.pdf|download|factsheet', re.IGNORECASE))
    print(f"\nDownload anchors: {len(download_anchors)}")
    for a in download_anchors[:10]:
        print(f"  href={a.get('href', '')[:120]}")
        print(f"  text={a.get_text(strip=True)[:80]}")
except:
    pass

# Show first 3000 chars
print(f"\n=== Page content (first 3000 chars) ===")
print(text[:3000])
