"""Find Tata MF factsheet API via Next.js data or JS chunks."""
import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

r = requests.get("https://www.tatamutualfund.com/information-documents/factsheets", headers=headers, timeout=15)
html = r.text

# Check for __NEXT_DATA__
nd_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
if nd_match:
    nd = json.loads(nd_match.group(1))
    print("=== __NEXT_DATA__ keys ===")
    print(json.dumps(list(nd.keys()), indent=2))
    if 'props' in nd:
        props = nd['props']
        print(f"\nprops keys: {list(props.keys())}")
        if 'pageProps' in props:
            pp = props['pageProps']
            print(f"pageProps keys: {list(pp.keys())}")
            # Print first 2000 chars of pageProps
            pp_str = json.dumps(pp, indent=2)
            print(f"\npageProps ({len(pp_str)} chars):\n{pp_str[:3000]}")
else:
    print("No __NEXT_DATA__ found")

# Search for API URLs in HTML
api_urls = re.findall(r'["\']((?:https?://)?[^"\']*(?:api|factsheet|cms)[^"\']*)["\']', html, re.IGNORECASE)
unique_apis = list(set(api_urls))
print(f"\nAPI/factsheet URLs found: {len(unique_apis)}")
for u in sorted(unique_apis)[:20]:
    print(f"  {u}")

# Search for betacms URLs (seen in PDF links)
betacms = re.findall(r'betacms[^"\']*', html)
print(f"\nbetacms references: {len(betacms)}")
for b in set(betacms):
    print(f"  {b[:200]}")
