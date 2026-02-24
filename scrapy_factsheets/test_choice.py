"""Probe Choice MF factsheet component chunk for PDF URLs."""
import requests
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# The factsheets component is in chunk 3804
chunks = [
    "/_next/static/chunks/3804.0c6aa292ecaf97d3.js",
    "/_next/static/chunks/9828-3906658a0ead5696.js",
    "/_next/static/chunks/6127-8bb88d6abfc85ae0.js",
]

for chunk_path in chunks:
    url = f"https://choicemf.com{chunk_path}"
    print(f"\n{'='*60}")
    print(f"Fetching: {chunk_path}")
    resp = requests.get(url, headers=headers, timeout=15)
    text = resp.text
    print(f"Size: {len(text)} chars")

    # Find PDF URLs
    pdf_urls = re.findall(r'https?://[^\s"\'\\,}]+\.pdf', text)
    if pdf_urls:
        print(f"\nPDF URLs: {len(pdf_urls)}")
        for p in list(set(pdf_urls))[:10]:
            print(f"  {p}")

    # Find static.choicemf.com references
    static_refs = re.findall(r'["\']([^"\']*static\.choicemf[^"\']*)["\']', text, re.IGNORECASE)
    if static_refs:
        print(f"\nstatic.choicemf refs: {len(static_refs)}")
        for s in list(set(static_refs))[:10]:
            print(f"  {s}")

    # Find factsheet/download references
    factsheet_refs = re.findall(r'["\']([^"\']*(?:factsheet|Factsheet|FACTSHEET)[^"\']*)["\']', text)
    if factsheet_refs:
        print(f"\nFactsheet refs: {len(factsheet_refs)}")
        for f in list(set(factsheet_refs))[:15]:
            if len(f) < 200:
                print(f"  {f}")

    # Find fetch/API calls
    fetch_calls = re.findall(r'(?:fetch|get|post)\s*\(["\']([^"\']+)["\']', text, re.IGNORECASE)
    if fetch_calls:
        print(f"\nFetch/API calls:")
        for f in list(set(fetch_calls))[:10]:
            print(f"  {f}")

    # Find any URL-like strings
    urls = re.findall(r'["\'](https?://[^"\']+)["\']', text)
    if urls:
        relevant = [u for u in set(urls) if 'choicemf' in u or 'factsheet' in u.lower() or '.pdf' in u.lower()]
        if relevant:
            print(f"\nRelevant URLs:")
            for u in relevant[:10]:
                print(f"  {u}")

    # Show context around 'factsheet' mentions
    for match in re.finditer(r'factsheet', text, re.IGNORECASE):
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 200)
        ctx = text[start:end]
        print(f"\n  Context: ...{ctx}...")
        break  # Just first occurrence per chunk
