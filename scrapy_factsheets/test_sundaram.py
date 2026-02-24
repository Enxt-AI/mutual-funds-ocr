"""Test Sundaram MF DownloadArchive API with correct pattern."""
import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.sundarammutual.com/fundwise-factsheet",
}

base_url = "https://www.sundarammutual.com/ajax/Modules_Forms_Downloads_Fundwise_Factsheet,App_Web_iwjfkxgb.ashx"
api_url = f"{base_url}?_method=DownloadArchive&_session=no"

# The body format from the JS: 'cat=' + enc(cat)+ '\r\nmnth=' + enc(mnth)
# cat=1 is the default, mnth is mm/yyyy format
for month_str in ["01/2026", "12/2025", "02/2026"]:
    body = f"cat=1\r\nmnth={month_str}"
    r = requests.post(api_url, headers=headers, data=body, timeout=10)
    print(f"\nmnth={month_str}: Status={r.status_code}, Size={len(r.text)}")
    print(f"Response: {r.text[:500]}")
