"""Dig into HSBC MF HTML structure for factsheet PDF links."""
import requests
from bs4 import BeautifulSoup
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

base = "https://www.assetmanagement.hsbc.co.in"
url = f"{base}/en/mutual-funds/investor-resources?Date=&Cap=&Doc=fund-factsheets"

r = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')

# Find elements containing "Fund factsheets" text (the category label)
print("=== Elements with 'Fund factsheets' text ===")
fs_elements = soup.find_all(string=re.compile(r'Fund factsheets', re.IGNORECASE))
print(f"Found: {len(fs_elements)}")

# For the first 3, navigate up to find the parent container and download link
for i, el in enumerate(fs_elements[:3]):
    print(f"\n--- Factsheet entry {i+1} ---")
    # Go up to find the article/card container
    parent = el.parent
    for _ in range(10):  # Walk up to 10 levels
        if parent is None:
            break
        # Check for links in this parent
        links = parent.find_all('a', href=True)
        if links:
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)[:80]
                if href and (href.endswith('.pdf') or 'download' in href.lower() or '/content/' in href):
                    print(f"  Link: {text} -> {href[:150]}")
            if any(l.get('href', '').endswith('.pdf') or 'download' in l.get('href', '').lower() for l in links):
                # Found the container with download links
                print(f"  Container tag: {parent.name}, class: {parent.get('class')}")
                # Print the full HTML of this container (truncated)
                html = str(parent)
                print(f"  HTML ({len(html)} chars): {html[:800]}")
                break
        parent = parent.parent

# Also check for all links on the page
print("\n\n=== All link patterns ===")
all_links = soup.find_all('a', href=True)
link_patterns = {}
for link in all_links:
    href = link.get('href', '')
    if '.pdf' in href.lower():
        # Categorize by domain/path
        parts = href.split('/')
        pattern = '/'.join(parts[:4]) if len(parts) > 4 else href[:60]
        link_patterns[pattern] = link_patterns.get(pattern, 0) + 1

print(f"Total links: {len(all_links)}")
print(f"PDF link patterns:")
for p, c in sorted(link_patterns.items(), key=lambda x: -x[1])[:10]:
    print(f"  {c}x: {p}")

# Show first 5 PDF links
pdf_count = 0
for link in all_links:
    href = link.get('href', '')
    if '.pdf' in href.lower():
        text = link.get_text(strip=True)[:80]
        print(f"\n  [{pdf_count+1}] {text}")
        print(f"      {href[:200]}")
        if 'factsheet' in text.lower() or 'asset' in text.lower():
            pdf_count += 1
            if pdf_count >= 5:
                break

# Check for data attributes that might contain PDF URLs
print("\n\n=== Data attributes with URLs ===")
for attr_name in ['data-href', 'data-url', 'data-download', 'data-file', 'data-link']:
    els = soup.find_all(attrs={attr_name: True})
    if els:
        print(f"\n  {attr_name}: {len(els)} elements")
        for e in els[:3]:
            print(f"    {e.get(attr_name, '')[:150]}")
