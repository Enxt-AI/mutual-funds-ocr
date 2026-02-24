"""Test if the direct PDF URL works (bypasses Akamai WAF)."""
import requests

headers = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Test 1: Direct PDF URL from earlier successful test
pdf_url = "https://www.edelweissmf.com/Files/downloads/FACTSHEETS/FACTSHEETS/2026/Jan/Published/Edelweiss Factsheet January 2026_12012026_092646_AM.pdf"
print(f"Testing direct PDF URL...")
resp = requests.head(pdf_url, headers=headers, timeout=10, allow_redirects=True)
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
print(f"Content-Length: {resp.headers.get('Content-Length', 'N/A')}")

if resp.status_code == 200:
    print("\nDirect PDF URL works! Downloading...")
    resp2 = requests.get(pdf_url, headers=headers, timeout=30)
    print(f"Download status: {resp2.status_code}, Size: {len(resp2.content)} bytes")
    
    if resp2.status_code == 200 and len(resp2.content) > 1000:
        import os
        save_dir = r"d:\OCR\OCR\Scraped Factsheets\edelweiss-mf"
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, "Edelweiss Factsheet January 2026.pdf")
        with open(filepath, "wb") as f:
            f.write(resp2.content)
        print(f"Saved: {filepath}")
else:
    print(f"Headers: {dict(resp.headers)}")
    # Try GET instead of HEAD
    print("\nTrying GET...")
    resp2 = requests.get(pdf_url, headers=headers, timeout=10)
    print(f"GET Status: {resp2.status_code}, Size: {len(resp2.content)} bytes")
