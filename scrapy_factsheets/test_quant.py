"""Analyze Quant MF factsheet page for PDF links and APIs."""
import requests
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

url = "https://quantmutual.com/downloads/factsheet"
r = requests.get(url, headers=headers, timeout=30)
html = r.text
print(f"Page: {r.status_code}, {len(html)} chars")

# Find PDF links
pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', html, re.IGNORECASE)
print(f"\nPDF links: {len(pdf_links)}")
for p in pdf_links[:10]:
    print(f"  {p}")

# Find all PDF URLs in page
all_pdfs = re.findall(r'https?://[^"\'<>\s]*\.pdf', html, re.IGNORECASE)
print(f"\nAll PDF URLs: {len(all_pdfs)}")
for p in all_pdfs[:5]:
    print(f"  {p}")

# Find factsheet mentions
for m in re.finditer(r'factsheet', html, re.IGNORECASE):
    s = max(0, m.start() - 50)
    e = min(len(html), m.end() + 200)
    ctx = html[s:e]
    if 'pdf' in ctx.lower() or 'api' in ctx.lower() or 'url' in ctx.lower() or 'href' in ctx:
        print(f"\nFactsheet context: ...{ctx[:300]}...")

# Find JS/API references
api_urls = re.findall(r'["\']((?:https?://|/)[^"\']*(?:api|factsheet|download)[^"\']*)["\']', html, re.IGNORECASE)
print(f"\nAPI/download URLs: {len(api_urls)}")
for u in sorted(set(api_urls))[:10]:
    if 'css' not in u and 'font' not in u:
        print(f"  {u}")

# Find script tags with factsheet-related content
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, script in enumerate(scripts):
    if 'factsheet' in script.lower() and len(script) > 50:
        print(f"\n=== Script [{i}] ({len(script)} chars) ===")
        # Find relevant sections
        for m in re.finditer(r'factsheet', script, re.IGNORECASE):
            s = max(0, m.start() - 100)
            e = min(len(script), m.end() + 300)
            print(f"  ...{script[s:e][:400]}...")

# Check for AJAX calls
ajax = re.findall(r'(?:ajax|fetch|axios|get|post)\s*\(\s*["\']([^"\']+)["\']', html, re.IGNORECASE)
print(f"\nAJAX calls: {ajax[:10]}")

# Check for data-src or lazy-load attributes
data_attrs = re.findall(r'data-(?:src|url|href|file)\s*=\s*"([^"]*factsheet[^"]*)"', html, re.IGNORECASE)
print(f"\nData attributes: {data_attrs[:10]}")
