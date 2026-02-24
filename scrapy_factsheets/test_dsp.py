"""Test DSP MF downloads.json API endpoint."""
import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}

# The actual API endpoint
url = "https://www.dspim.com/downloads.json"
params = {
    "page": "1",
    "per_page": "10",
    "category": "Information Documents",
    "sub_category": "Factsheets",
    "sort_by": "latest",
}

print(f"Testing API: {url}")
resp = requests.get(url, params=params, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type')}")

if resp.status_code == 200:
    data = resp.json()
    print(f"\nTop keys: {list(data.keys())}")
    
    if 'data' in data:
        items = data['data']
        print(f"Items count: {len(items)}")
        if items:
            print(f"\nFirst item keys: {list(items[0].keys())}")
            for item in items[:5]:
                print(f"\n  Title: {item.get('title', 'N/A')}")
                print(f"  PDF URL: {item.get('pdf_url', 'N/A')}")
                print(f"  Category: {item.get('category', 'N/A')}")
                print(f"  Sub-category: {item.get('sub_category', 'N/A')}")
                print(f"  Month: {item.get('month', 'N/A')}")
                print(f"  Year: {item.get('year', 'N/A')}")
    
    print(f"\n=== Full response (first 3000 chars) ===")
    print(json.dumps(data, indent=2)[:3000])
else:
    print(f"Response: {resp.text[:500]}")
