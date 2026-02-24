"""Test Mirae Asset factsheet API and find EncryptFunction."""
import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json;charset=utf-8",
    "Origin": "https://www.miraeassetmf.co.in",
    "Referer": "https://www.miraeassetmf.co.in/downloads/factsheet",
}

# First find EncryptFunction in the JS
url_main = "https://www.miraeassetmf.co.in/main.js?v=xaCIERuFlYn-32jPLwfimvrV-iNVDZMb59U4PXX1fIY1"
r = requests.get(url_main, headers={"User-Agent": headers["User-Agent"]}, timeout=15)
js = r.text

print("=== EncryptFunction ===")
for m in re.finditer(r'EncryptFunction|DecryptFunction|encryptfunction', js, re.IGNORECASE):
    start = max(0, m.start() - 50)
    end = min(len(js), m.end() + 500)
    print(f"  ...{js[start:end][:550]}...")
    print()

# Also check DownloadFactsheet.js for EncryptFunction
url_dl = "https://www.miraeassetmf.co.in/DownloadFactsheet.js?v=8rdUwOUWYhmWgJ08XXQOpaaheXJ5OFpnFb4ICAxo_bI1"
r2 = requests.get(url_dl, headers={"User-Agent": headers["User-Agent"]}, timeout=15)
js2 = r2.text
for m in re.finditer(r'EncryptFunction|DecryptFunction|CryptoJS|encrypt', js2, re.IGNORECASE):
    start = max(0, m.start() - 50)
    end = min(len(js2), m.end() + 300)
    print(f"  DL: ...{js2[start:end][:350]}...")
    print()

# Try calling the API without encryption first
print("\n=== Testing API without encryption ===")
payload = {"modulename": "Factsheet", "pgno": 1, "pgsize": 10}
try:
    r3 = requests.post(
        "https://www.miraeassetmf.co.in/AjaxService/GetDownloadsDataAsync",
        json=payload, headers=headers, timeout=15
    )
    print(f"Status: {r3.status_code}")
    print(f"Response: {r3.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Try GetFactsheetDownload
print("\n=== Testing GetFactsheetDownload ===")
try:
    r4 = requests.post(
        "https://www.miraeassetmf.co.in/AjaxService/GetFactsheetDownload",
        json={"navAnchorId": "nav-fact-tab1"}, headers=headers, timeout=15
    )
    print(f"Status: {r4.status_code}")
    print(f"Response: {r4.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Try GetDownloadsData
print("\n=== Testing GetDownloadsData ===")
try:
    r5 = requests.post(
        "https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData",
        json=payload, headers=headers, timeout=15
    )
    print(f"Status: {r5.status_code}")
    print(f"Response: {r5.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
