"""Test Navi MF REST API with correct nonce header."""
import requests
import re
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
})

# Step 1: Get page to establish session and extract nonce
url = "https://navi.com/mutual-fund/downloads/factsheet"
r = session.get(url, timeout=30)
html = r.text
print(f"Page cookies: {dict(session.cookies)}")

# Extract nonce
nonce_match = re.search(r'"nonce"\s*:\s*"([^"]+)"', html)
nonce = nonce_match.group(1) if nonce_match else ""
print(f"Nonce: {nonce}")

# Step 2: Call the REST API with different header combos
api_url = "https://navi.com/wp-json/nv/v1/documents"
params = {
    "category": "867",
    "type": "Monthly",
    "financial_year": "2025-2026",
    "value": "January",
    "order": "DESC",
}

# Try different header names
for header_name in ["WP-NONCE", "X-WP-Nonce", "WP-Nonce"]:
    r2 = session.post(api_url, data=params, headers={header_name: nonce}, timeout=15)
    status = "OK" if r2.status_code == 200 else f"FAIL ({r2.status_code})"
    preview = r2.text[:200] if r2.status_code != 200 else r2.text[:500]
    print(f"\n{header_name}: {status}")
    print(f"  {preview}")
    if r2.status_code == 200:
        break

# If all header combos fail, try without value
if r2.status_code != 200:
    print("\n=== Trying without value, just category + type ===")
    params2 = {"category": "867", "type": "Monthly", "order": "DESC"}
    for header_name in ["WP-NONCE", "X-WP-Nonce"]:
        r3 = session.post(api_url, data=params2, headers={header_name: nonce}, timeout=15)
        print(f"\n{header_name}: {r3.status_code}")
        print(f"  {r3.text[:500]}")
        if r3.status_code == 200:
            break

# Try with duration select option values
print("\n=== Find duration options in HTML ===")
# Find select[name=duration] options
dur_match = re.search(r'name="duration".*?</select>', html, re.DOTALL)
if dur_match:
    opts = re.findall(r'<option[^>]*value="([^"]*)"', dur_match.group())
    print(f"Duration options: {opts[:15]}")
