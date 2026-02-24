"""Test correct filter param and check node for Taurus MF."""
import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}
ajax_headers = {**headers, "X-Requested-With": "XMLHttpRequest"}

# Test 1: Views AJAX with correct filter name
url = "https://www.taurusmutualfund.com/views/ajax"
data = {
    "view_name": "factsheet",
    "view_display_id": "page_1",
    "view_args": "",
    "view_path": "/factsheet",
    "view_dom_id": "d5f1e851a8167d48810530ac5ad4dde4d1ac38259574f15c0a76e45b3485a3b5",
    "pager_element": "0",
    "field_factsheet_item_target_id": "565",
    "_drupal_ajax": "1",
}
r = requests.post(url, headers=ajax_headers, data=data, timeout=10)
print(f"=== Views AJAX with field_factsheet_item_target_id=565 ===")
try:
    result = json.loads(r.text)
    for item in result:
        if item.get("command") == "insert" and "data" in item:
            d = item["data"]
            pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', d)
            all_links = re.findall(r'href="([^"]*)"', d)
            if pdfs:
                print(f"PDFs: {pdfs[:10]}")
            print(f"All links ({len(all_links)}): {all_links[:15]}")
            text = re.sub(r'<[^>]+>', ' ', d)
            text = re.sub(r'\s+', ' ', text).strip()
            print(f"Text: {text[:500]}")
except:
    print(f"Error: {r.text[:500]}")

# Test 2: Check node/32693
print("\n=== Node /node/32693 ===")
r2 = requests.get("https://www.taurusmutualfund.com/node/32693", headers=headers, timeout=10)
print(f"Status: {r2.status_code}, Size: {len(r2.text)}")
pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', r2.text)
print(f"PDFs: {pdfs[:20]}")
# Find factsheet file links
fs = re.findall(r'href="([^"]*(?:factsheet|Factsheet)[^"]*)"', r2.text)
print(f"Factsheet links: {fs[:10]}")
# Find all file links
files = re.findall(r'href="(/sites/default/files/[^"]*)"', r2.text)
print(f"File links: {files[:10]}")
# Show title
title = re.search(r'<title>([^<]+)</title>', r2.text)
if title: print(f"Title: {title.group(1)}")
# Show body text
text = re.sub(r'<[^>]+>', ' ', r2.text)
text = re.sub(r'\s+', ' ', text).strip()
# Find factsheet-related text
for m in re.finditer(r'(?:factsheet|january|february|2026|2025)', text, re.IGNORECASE):
    print(f"Context @{m.start()}: {text[max(0,m.start()-30):m.end()+100]}")
    if len([x for x in re.finditer(r'(?:factsheet|january|february|2026|2025)', text[max(0,m.start()-30):m.end()+100], re.IGNORECASE)]) > 0:
        break

# Test 3: Try factsheet page with query string
print("\n=== /factsheet?field_factsheet_item_target_id=565 ===")
r3 = requests.get("https://www.taurusmutualfund.com/factsheet?field_factsheet_item_target_id=565", headers=headers, timeout=10)
print(f"Status: {r3.status_code}, Size: {len(r3.text)}")
pdfs3 = re.findall(r'href="([^"]*\.pdf[^"]*)"', r3.text)
print(f"Total PDFs: {len(pdfs3)}")
# exclude nav PDFs
content_pdfs = [p for p in pdfs3 if 'factsheet' in p.lower() or 'Factsheet' in p]
print(f"Factsheet PDFs: {content_pdfs[:10]}")
fs_files = re.findall(r'href="(/sites/default/files/[^"]*factsheet[^"]*)"', r3.text, re.IGNORECASE)
print(f"Factsheet file links: {fs_files[:10]}")
