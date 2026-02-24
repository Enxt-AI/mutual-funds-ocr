"""Analyze Zerodha Fund House fund documents page."""
import requests
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

r = requests.get("https://www.zerodhafundhouse.com/resources/fund-documents", headers=headers, timeout=15)
html = r.text
print(f"Status: {r.status_code}, Size: {len(html)}")

# Check if it's a Next.js/React app
is_nextjs = '__next' in html or '__NEXT' in html
is_nuxt = '__NUXT' in html
is_react = 'react' in html.lower() or '_app' in html
print(f"Next.js: {is_nextjs}, Nuxt: {is_nuxt}, React: {is_react}")

# Find meta/framework indicators
frameworks = re.findall(r'(next|nuxt|gatsby|angular|vue|react)', html[:5000], re.IGNORECASE)
print(f"Framework hints: {list(set(frameworks))}")

# Find all PDF links
pdf_urls = re.findall(r'https?://[^"\\,\}\]\s]*\.pdf', html, re.IGNORECASE)
print(f"\nPDF URLs: {len(pdf_urls)}")
for p in list(set(pdf_urls))[:15]:
    print(f"  {p}")

# Look for factsheet mentions
factsheet_matches = list(re.finditer(r'factsheet', html, re.IGNORECASE))
print(f"\nFactsheet mentions: {len(factsheet_matches)}")
for m in factsheet_matches[:5]:
    ctx = html[max(0,m.start()-100):m.end()+200]
    print(f"  {ctx[:300]}")

# Look for API endpoints / data URLs
api_urls = re.findall(r'https?://[^"\\,\}\]\s]*(?:api|graphql|json)[^"\\,\}\]\s]*', html, re.IGNORECASE)
print(f"\nAPI URLs: {len(api_urls)}")
for u in list(set(api_urls))[:10]:
    print(f"  {u}")

# Look for __NEXT_DATA__ or initial props
next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if next_data:
    import json
    data = json.loads(next_data.group(1))
    print(f"\n__NEXT_DATA__ found! buildId: {data.get('buildId')}")
    props = data.get('props', {}).get('pageProps', {})
    print(f"pageProps keys: {list(props.keys())[:20]}")
    
    # Look for fund documents data
    docs_data = str(props)[:3000]
    print(f"\nProps preview: {docs_data}")

# Check for script tags with data
script_data = re.findall(r'<script[^>]*>(.*?)</script>', html[:50000], re.DOTALL)
print(f"\nScript tags: {len(script_data)}")
for i, s in enumerate(script_data):
    if 'factsheet' in s.lower() or 'document' in s.lower():
        print(f"  Script {i}: {s[:300]}")
