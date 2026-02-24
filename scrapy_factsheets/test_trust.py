"""Find Trust MF GraphQL query for factsheets and test it."""
import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Fetch JS bundle and look for download/factsheet GraphQL area
r = requests.get("https://www.trustmf.com/assets/index-C_2xml-C.js", headers=headers, timeout=30)
js = r.text

# Look at the factsheet code area around position 1131401
start = 1130000
end = 1145000
chunk = js[start:end]

# Find all GraphQL query strings in that chunk 
queries = re.findall(r'`([^`]*(?:query|mutation)[^`]*)`', chunk)
print(f"GraphQL queries in factsheet area: {len(queries)}")
for q in queries[:5]:
    print(f"  {q[:300]}")

# Find all graphql mentions near downloads
for pattern in [r'graphql', r'useQuery', r'gql', r'GRAPHQL']:
    matches = [(m.start()+start, chunk[max(0,m.start()-100):m.end()+200]) 
               for m in re.finditer(pattern, chunk)]
    if matches:
        print(f"\n=== '{pattern}' in factsheet area ({len(matches)} matches) ===")
        for pos, ctx in matches[:3]:
            print(f"  @{pos}: {ctx[:300]}")

# Look for download category/tag query
for pattern in [r'category', r'downloadFile', r'mediaItem', r'sourceUrl', r'fileUrl']:
    matches = [(m.start()+start, chunk[max(0,m.start()-100):m.end()+200]) 
               for m in re.finditer(pattern, chunk, re.IGNORECASE)]
    if matches:
        print(f"\n=== '{pattern}' ({len(matches)} matches) ===")
        for pos, ctx in matches[:3]:
            print(f"  @{pos}: {ctx[:300]}")

# Try simple WordPress REST API for posts with factsheet category
wp_base = "https://www.trustmf.com/trustmfsys"
for endpoint in [
    f"{wp_base}/wp-json/wp/v2/posts?search=factsheet&per_page=5",
    f"{wp_base}/wp-json/wp/v2/media?search=factsheet&per_page=5",
    f"{wp_base}/wp-json/wp/v2/categories?search=factsheet",
    f"{wp_base}/wp-json/wp/v2/pages?search=downloads",
]:
    try:
        r2 = requests.get(endpoint, headers=headers, timeout=5)
        print(f"\n{endpoint.split('trustmfsys')[1]}: {r2.status_code}")
        if r2.status_code == 200:
            data = r2.json()
            if isinstance(data, list):
                for item in data[:3]:
                    title = item.get('title', {})
                    if isinstance(title, dict):
                        title = title.get('rendered', '')
                    print(f"  - {title} | {item.get('slug', '')} | id={item.get('id', '')}")
                    if 'source_url' in item:
                        print(f"    URL: {item['source_url']}")
    except Exception as e:
        print(f"  Error: {e}")
