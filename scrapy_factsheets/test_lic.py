"""Analyze LIC MF factsheet page for PDF links."""
import requests
import re
import urllib3
from bs4 import BeautifulSoup
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

url = "https://www.licmf.com/downloads/factsheet"
r = requests.get(url, headers=headers, timeout=15, verify=False)
print(f"Status: {r.status_code}, {len(r.text)} chars")

soup = BeautifulSoup(r.text, 'html.parser')

# Find all PDF links
pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
print(f"\nPDF links: {len(pdf_links)}")
for link in pdf_links[:20]:
    text = link.get_text(strip=True)[:80]
    href = link.get('href', '')
    print(f"  {text}: {href[:200]}")

# Find factsheet-specific links
print("\n=== Factsheet-specific links ===")
for link in soup.find_all('a', href=True):
    href = link.get('href', '')
    text = link.get_text(strip=True)
    if 'factsheet' in (text + href).lower() and href.endswith('.pdf'):
        print(f"  {text[:60]}: {href[:200]}")

# Check for download buttons/links in the current section
current_section = soup.find('div', id='current') or soup.find(id='current')
if current_section:
    print("\n=== Current section ===")
    links = current_section.find_all('a', href=True)
    for link in links[:10]:
        print(f"  {link.get_text(strip=True)[:60]}: {link['href'][:200]}")
else:
    # Try to find any section with factsheet
    print("\n=== Searching for factsheet sections ===")
    for div in soup.find_all(['div', 'section'], class_=True):
        cls = ' '.join(div.get('class', []))
        if 'fact' in cls.lower() or 'download' in cls.lower() or 'current' in cls.lower():
            print(f"  <{div.name} class='{cls}'>")
            links = div.find_all('a', href=True)
            for link in links[:5]:
                print(f"    {link.get_text(strip=True)[:60]}: {link['href'][:200]}")
