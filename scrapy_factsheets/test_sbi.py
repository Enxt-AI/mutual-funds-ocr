"""Test SBI MF GetRecentFactSheets API."""
import requests
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json;charset=utf-8",
    "Referer": "https://www.sbimf.com/factsheets",
}

# Test GetRecentFactSheets
url = "https://www.sbimf.com/ajaxcall/CMS/GetRecentFactSheets"
r = requests.post(url, headers=headers, json=None, timeout=15)
print(f"Status: {r.status_code}, {len(r.text)} chars")
print(f"Content-Type: {r.headers.get('Content-Type', '')}")

# Parse the returned HTML for PDF links
html = r.text
pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', html, re.IGNORECASE)
print(f"\nPDF links: {len(pdf_links)}")
for p in pdf_links[:10]:
    print(f"  {p}")

# Show first 2000 chars
print(f"\nResponse (first 2000 chars):\n{html[:2000]}")
