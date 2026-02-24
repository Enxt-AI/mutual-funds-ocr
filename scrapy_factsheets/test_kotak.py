"""Analyze Kotak MF factsheet page for API endpoints."""
import requests
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# First get the page to find the JS bundle
r = requests.get("https://www.kotakmf.com/Information/forms-and-downloads/Factsheet", headers=headers, timeout=15)
print(f"Page: {r.status_code}, {len(r.text)} chars")

# Find JS files
scripts = re.findall(r'src="([^"]*\.js[^"]*)"', r.text)
print(f"\nJS files: {len(scripts)}")
for s in scripts:
    print(f"  {s}")

# Look for inline scripts with API info
inline_matches = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
for i, script in enumerate(inline_matches):
    if len(script) > 100 and any(x in script.lower() for x in ['api', 'factsheet', 'download', 'environment']):
        print(f"\n=== Inline script [{i}] ({len(script)} chars) ===")
        # Find URLs  
        urls = re.findall(r'["\'](https?://[^"\']+)["\']', script)
        for u in urls[:10]:
            print(f"  URL: {u}")

# Try the main app JS
main_js = [s for s in scripts if 'main' in s.lower()]
if main_js:
    js_url = main_js[0]
    if not js_url.startswith('http'):
        js_url = f"https://www.kotakmf.com{js_url}"
    print(f"\nFetching main JS: {js_url}")
    r2 = requests.get(js_url, headers=headers, timeout=30)
    js = r2.text
    print(f"Size: {len(js)} chars")
    
    # API base URLs
    api_urls = re.findall(r'["\'](https?://[^"\']*(?:api|service|gateway)[^"\']*)["\']', js, re.IGNORECASE)
    print(f"\n=== API URLs ===")
    for u in sorted(set(api_urls)):
        if len(u) < 200:
            print(f"  {u}")
    
    # Factsheet/download patterns
    print(f"\n=== Factsheet context ===")
    for m in re.finditer(r'[Ff]act[Ss]heet', js):
        start = max(0, m.start() - 100)
        end = min(len(js), m.end() + 200)
        ctx = js[start:end]
        if any(x in ctx.lower() for x in ['url', 'api', 'http', 'pdf', 'download', 'get', 'post']):
            print(f"  ...{ctx[:300]}...")
            print()
    
    # Environment/config
    print(f"\n=== Environment config ===")
    for m in re.finditer(r'(?:environment|apiUrl|apiBase|baseUrl|base_url|BASE_URL)', js, re.IGNORECASE):
        start = max(0, m.start() - 50)
        end = min(len(js), m.end() + 300)
        print(f"  ...{js[start:end][:350]}...")
        print()
