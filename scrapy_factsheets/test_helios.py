"""Analyze Helios MF downloads page."""
import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

url = "https://www.heliosmf.in/downloads/"
print(f"Fetching {url}...")
r = requests.get(url, headers=headers, timeout=15)
print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('Content-Type', '')}")
print(f"Body length: {len(r.text)} chars")

if r.status_code == 200:
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Find all PDF links
    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
    print(f"\nPDF links found: {len(pdf_links)}")
    for link in pdf_links:
        text = link.get_text(strip=True)
        href = link.get('href', '')
        if 'factsheet' in text.lower() or 'factsheet' in href.lower():
            print(f"  [FACTSHEET] {text}: {href}")
        else:
            print(f"  {text[:60]}: {href[:100]}")
    
    # Look for factsheet mentions
    factsheet_elements = soup.find_all(string=re.compile(r'factsheet', re.IGNORECASE))
    if factsheet_elements:
        print(f"\nFactsheet mentions: {len(factsheet_elements)}")
        for el in factsheet_elements[:10]:
            parent = el.parent
            print(f"  Tag: {parent.name}, Text: {el.strip()[:80]}")
            # Check if parent has a link
            link = parent.find('a') if parent else None
            if link:
                print(f"    Link: {link.get('href', '')}")
    
    # Look for download buttons/sections
    download_sections = soup.find_all(['div', 'section'], class_=re.compile(r'download|factsheet', re.IGNORECASE))
    print(f"\nDownload/factsheet sections: {len(download_sections)}")
    for sec in download_sections[:5]:
        print(f"  Class: {sec.get('class')}, Text: {sec.get_text(strip=True)[:100]}")
    
    # Check for JS-rendered content or API calls
    scripts = soup.find_all('script', src=True)
    print(f"\nExternal scripts: {len(scripts)}")
    for s in scripts:
        src = s.get('src', '')
        if 'chunk' in src or 'main' in src or 'app' in src:
            print(f"  {src}")
    
    # Print first 2000 chars of body text to understand structure
    body_text = soup.get_text(separator='\n', strip=True)
    print(f"\n=== Page text (first 2000 chars) ===")
    print(body_text[:2000])
else:
    print(f"\nResponse headers: {dict(r.headers)}")
    print(f"Body: {r.text[:500]}")
