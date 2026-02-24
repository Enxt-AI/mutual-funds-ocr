"""Analyze Mahindra Manulife MF downloads page for factsheet links."""
import requests
import re
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

url = "https://www.mahindramanulife.com/downloads"
print(f"Fetching {url}...")
try:
    r = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {r.status_code}, {len(r.text)} chars")
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # PDF links
    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
    print(f"\nPDF links: {len(pdf_links)}")
    for link in pdf_links[:20]:
        text = link.get_text(strip=True)[:80]
        href = link.get('href', '')
        if 'factsheet' in (text + href).lower():
            print(f"  [FACTSHEET] {text}: {href[:200]}")
    
    # All factsheet references
    print("\n=== All factsheet references ===")
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if 'factsheet' in (text + href).lower() or 'fact-sheet' in (text + href).lower():
            print(f"  {text[:60]}: {href[:200]}")
    
    # Check for JS SPA
    scripts = soup.find_all('script', src=True)
    print(f"\nScript tags with src: {len(scripts)}")
    for s in scripts[:5]:
        src = s.get('src', '')
        if any(x in src.lower() for x in ['main', 'app', 'chunk', '_next', 'bundle']):
            print(f"  {src[:150]}")
    
    # API clues in inline scripts
    for s in soup.find_all('script'):
        text = s.string or ''
        if 'factsheet' in text.lower() or 'api' in text.lower():
            urls = re.findall(r'["\'](https?://[^"\']+)["\']', text)
            if urls:
                for u in urls[:5]:
                    print(f"  Inline URL: {u[:150]}")

except Exception as e:
    print(f"Error: {e}")
    # Try alternative approach
    print("\nTrying with verify=False...")
    try:
        r = requests.get(url, headers=headers, timeout=30, verify=False)
        print(f"Status: {r.status_code}, {len(r.text)} chars")
        # Quick check for factsheet
        factsheet_urls = re.findall(r'(https?://[^"\']*factsheet[^"\']*\.pdf)', r.text, re.IGNORECASE)
        for u in factsheet_urls[:10]:
            print(f"  {u}")
        if not factsheet_urls:
            factsheet_urls = re.findall(r'href=["\']([^"\']*factsheet[^"\']*)["\']', r.text, re.IGNORECASE)
            for u in factsheet_urls[:10]:
                print(f"  href: {u}")
    except Exception as e2:
        print(f"Also failed: {e2}")
