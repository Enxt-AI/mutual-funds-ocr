"""Test Axis MF API with different parameter formats and endpoints."""
import requests
import json

headers = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.axismf.com/downloads?formType=Factsheet",
}

# 1. Try CMS API without any params
print("=== No params ===")
url = "https://www.axismf.com/cms/api/factsheet"
resp = requests.get(url, headers=headers, timeout=10)
print(f"Status: {resp.status_code}, Content-Type: {resp.headers.get('Content-Type')}")
print(f"Body: {resp.text[:1000]}")

# 2. Try different month formats  
print("\n=== Different month formats ===")
for month_val in ["January", "Jan", "01", "1", "february", "Feb"]:
    url = f"https://www.axismf.com/cms/api/factsheet?year=2025&month={month_val}"
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json() if resp.headers.get('Content-Type','').startswith('application/json') else None
    print(f"  month={month_val}: {data if data else resp.status_code}")

# 3. Try other CMS API endpoints
print("\n=== Other CMS API endpoints ===")
for endpoint in [
    "downloads-latest-updates",
    "downloads",
    "download",
    "factsheet/latest",
    "node/factsheet",
    "content/factsheet",
]:
    url = f"https://www.axismf.com/cms/api/{endpoint}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        ct = resp.headers.get('Content-Type', '')
        body = resp.text[:200]
        is_html = body.strip().startswith('<!DOCTYPE') or body.strip().startswith('<html')
        if not is_html:
            print(f"  {endpoint}: Status={resp.status_code}, CT={ct}")
            print(f"    Body: {body[:300]}")
        else:
            print(f"  {endpoint}: HTML (SPA shell)")
    except Exception as e:
        print(f"  {endpoint}: Error - {e}")

# 4. Try the api/v1 path with JSON accept
print("\n=== api/v1 endpoints ===")
for endpoint in [
    "factsheet",
    "downloads-latest-updates",
    "downloads",
]:
    url = f"https://www.axismf.com/api/v1/{endpoint}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        ct = resp.headers.get('Content-Type', '')
        body = resp.text[:200]
        is_html = body.strip().startswith('<!DOCTYPE') or body.strip().startswith('<html')
        if not is_html:
            print(f"  {endpoint}: Status={resp.status_code}, CT={ct}")
            print(f"    Body: {body[:300]}")
        else:
            print(f"  {endpoint}: HTML (SPA shell)")
    except Exception as e:
        print(f"  {endpoint}: Error - {e}")

# 5. Check CMS static files for factsheets
print("\n=== CMS static file check ===")
for path in [
    "cms/sites/default/files/pdf/",
    "cms/sites/default/files/factsheet/",
    "axisdownload/",
]:
    url = f"https://www.axismf.com/{path}"
    try:
        resp = requests.get(url, headers=headers, timeout=5, allow_redirects=False)
        print(f"  {path}: Status={resp.status_code}")
    except Exception as e:
        print(f"  {path}: Error - {e}")
