"""Analyze UNIFI MF factsheet page."""
import requests
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

r = requests.get("https://unifimf.com/factsheet/", headers=headers, timeout=15, verify=False)
print(f"Status: {r.status_code}, Size: {len(r.text)}")

if r.status_code == 200:
    html = r.text
    
    # Find PDF links
    pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', html, re.IGNORECASE)
    print(f"\nPDF links: {len(pdfs)}")
    for p in pdfs[:20]:
        print(f"  {p}")

    # Find factsheet-related links
    fs = re.findall(r'href="([^"]*factsheet[^"]*)"', html, re.IGNORECASE)
    print(f"\nFactsheet links: {len(fs)}")
    for f in fs[:10]:
        print(f"  {f}")

    # Check if WordPress
    if 'wp-content' in html:
        print("\n=== WordPress site ===")
    if 'wp-json' in html:
        print("Has wp-json link")

    # Look for download links or buttons
    for pattern in ['download', 'factsheet', '.pdf']:
        matches = [(m.start(), html[max(0,m.start()-100):m.end()+200]) 
                   for m in re.finditer(pattern, html, re.IGNORECASE)]
        if matches:
            print(f"\n=== '{pattern}' ({len(matches)} matches) ===")
            for pos, ctx in matches[:5]:
                ctx_clean = re.sub(r'\s+', ' ', ctx)
                print(f"  @{pos}: {ctx_clean[:300]}")
else:
    print(f"Response: {r.text[:500]}")
    print(f"\nHeaders: {dict(r.headers)}")
