"""Brute-force query params for ICICI /nms/v1/downloads/files endpoint."""
import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.icicipruamc.com",
    "Referer": "https://www.icicipruamc.com/media-center/downloads",
}

api = "https://apimf.icicipruamc.com"
base_ep = f"{api}/nms/v1/downloads/files"

# Try path-based patterns
path_tests = [
    # Category as path segment
    f"{base_ep}/factsheets",
    f"{base_ep}/Factsheets",
    f"{base_ep}/FACTSHEETS",
    f"{base_ep}/historical-factsheets",
    f"{base_ep}/Historical%20Factsheets",
    f"{base_ep}/PRODUCT_FACTSHEETS",
    f"{base_ep}/fund-factsheets",
    f"{base_ep}/all",
    # Different nesting
    f"{api}/nms/v1/downloads/factsheets",
    f"{api}/nms/v1/downloads/PRODUCT_FACTSHEETS",
    f"{api}/nms/v1/downloads/files/PRODUCT_FACTSHEETS",
]

# Try query param combos
param_tests = [
    {"category": "Factsheets"},
    {"category": "Historical Factsheets"},
    {"category": "PRODUCT_FACTSHEETS"},
    {"category": "FACTSHEETS"},
    {"subCategory": "Factsheets"},
    {"subCategory": "PRODUCT_FACTSHEETS"},
    {"subCategory": "Historical Factsheets"},
    {"type": "factsheet"},
    {"type": "FACTSHEET"},
    {"tab": "Historical Factsheets"},
    {"currentTabFilter": "Historical Factsheets"},
    {"title": "Historical Factsheets"},
    {"title": "Factsheets"},
    {"internalName": "PRODUCT_FACTSHEETS"},
    {"componentId": "PRODUCT_FACTSHEETS"},
    # Multi-param combos
    {"category": "CATEGORY_OF_MATERIAL", "subCategory": "PRODUCT_FACTSHEETS"},
    {"category": "CATEGORY_OF_MATERIAL", "title": "PRUDENT_RELATED_MATERIALS", "subCategory": "PRODUCT_FACTSHEETS"},
]

print("=== Path-based tests ===")
for url in path_tests:
    try:
        r = requests.get(url, headers=headers, timeout=8)
        short = url.replace(api, "")
        status_text = ""
        if "Resource not found" in r.text:
            status_text = "API 404"
        elif r.text.startswith("Original"):
            status_text = f"Wrapped ({r.text[:60]})"
        elif r.status_code == 200 and len(r.text) > 200:
            status_text = f"DATA! {len(r.text)} chars"
        else:
            status_text = f"{r.status_code} ({len(r.text)})"
        print(f"  {short}: {status_text}")
    except:
        print(f"  {short}: TIMEOUT")

print("\n=== Query param tests ===")
for params in param_tests:
    try:
        r = requests.get(base_ep, params=params, headers=headers, timeout=8)
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        status_text = ""
        if "Resource not found" in r.text:
            status_text = "API 404"
        elif len(r.text) > 200 and "statusCode" not in r.text:
            status_text = f"DATA! {len(r.text)} chars"
            try:
                data = r.json()
                if isinstance(data, dict):
                    print(f"  ?{param_str}: {status_text} keys={list(data.keys())[:10]}")
                    continue
                elif isinstance(data, list):
                    print(f"  ?{param_str}: {status_text} list[{len(data)}]")
                    if data and isinstance(data[0], dict):
                        print(f"    first: {json.dumps(data[0])[:200]}")
                    continue
            except:
                pass
        else:
            status_text = f"{r.status_code} ({len(r.text)})"
        print(f"  ?{param_str}: {status_text}")
    except:
        print(f"  ?{param_str}: TIMEOUT")

# Also try the Azure blob storage directly
print("\n=== Azure blob tests ===")
blob_tests = [
    "https://www.icicipruamc.com/blob/downloads/Historical Factsheets",
    "https://www.icicipruamc.com/blob/downloads/Factsheets/Complete Factsheet",
    "https://cmsstorageincdev.blob.core.windows.net/downloads",
    "https://cmsstorageincdev.blob.core.windows.net/downloads/factsheets",
]
for url in blob_tests:
    try:
        r = requests.get(url, headers=headers, timeout=8)
        print(f"  {url.split('.com/')[-1] if '.com/' in url else url.split('.net/')[-1]}: {r.status_code} ({r.headers.get('Content-Type','')})")
    except:
        print(f"  {url}: TIMEOUT")
