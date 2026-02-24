"""Analyze Nippon India MF factsheet page for PDF links and APIs."""
import requests
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

url = "https://mf.nipponindiaim.com/investor-service/downloads/factsheet-portfolio-and-other-disclosures"
r = requests.get(url, headers=headers, timeout=30)
html = r.text
print(f"Status: {r.status_code}, {len(html)} chars")

# Check for PDF links
pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', html, re.IGNORECASE)
print(f"\nPDF links: {len(pdf_links)}")
for p in pdf_links[:10]:
    if 'factsheet' in p.lower():
        print(f"  [FACTSHEET] {p[:200]}")

# All factsheet PDF links
factsheet_pdfs = [p for p in pdf_links if 'factsheet' in p.lower()]
print(f"\nFactsheet PDFs: {len(factsheet_pdfs)}")
for p in factsheet_pdfs[:5]:
    print(f"  {p[:200]}")

# Check for API endpoints
api_urls = re.findall(r'["\'](https?://[^"\']*api[^"\']*)["\']', html, re.IGNORECASE)
api_urls += re.findall(r'["\'](/api/[^"\']*)["\']', html, re.IGNORECASE)
print(f"\nAPI URLs: {len(api_urls)}")
for u in sorted(set(api_urls)):
    if 'google' not in u.lower() and len(u) < 200:
        print(f"  {u}")

# Check for Angular/React  
if 'ng-app' in html or 'angular' in html.lower():
    print("\n*** Angular app detected ***")
if '__NEXT_DATA__' in html:
    print("\n*** Next.js app detected ***")
if 'react' in html.lower():
    print("\n*** React app detected ***")

# Check inline scripts for AJAX or factsheet data
for i, m in enumerate(re.finditer(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)):
    script = m.group(1)
    if len(script) > 100 and ('factsheet' in script.lower() or 'ajax' in script.lower()):
        print(f"\n=== Inline script [{i}] ({len(script)} chars) ===")
        # Find relevant context
        for fm in re.finditer(r'factsheet|ajax|\.pdf', script, re.IGNORECASE):
            s = max(0, fm.start() - 50)
            e = min(len(script), fm.end() + 200)
            print(f"  ...{script[s:e][:300]}...")
        if len(script) < 500:
            print(f"  Full: {script}")
