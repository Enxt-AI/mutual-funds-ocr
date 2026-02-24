"""Test Jio BlackRock Next.js Server Action for factsheet data."""
import requests
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "text/x-component",
    "Content-Type": "text/plain;charset=UTF-8",
    "Origin": "https://www.jioblackrockamc.com",
    "Referer": "https://www.jioblackrockamc.com/statutory-disclosure/fund-documents/factsheet",
    "Next-Action": "60c09b509b7c9285121790d68606ebca78d1b505c6",
    "next-router-state-tree": '%5B%22%22%2C%7B%22children%22%3A%5B%22(public)%22%2C%7B%22children%22%3A%5B%22statutory-disclosure%22%2C%7B%22children%22%3A%5B%5B%22l1Id%22%2C%22fund-documents%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%5B%22l2Id%22%2C%22factsheet%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
}

url = "https://www.jioblackrockamc.com/statutory-disclosure/fund-documents/factsheet"

# Try January (user confirmed it has data)
payload = '["factsheet",{"year":"$undefined","month":"January","date":"$undefined"}]'
print(f"POST {url}")
print(f"Payload: {payload}")

r = requests.post(url, data=payload, headers=headers, timeout=15)
print(f"Status: {r.status_code}, {len(r.text)} chars")
print(f"Content-Type: {r.headers.get('Content-Type', '')}")

# RSC wire format - print raw
print(f"\n=== Raw response (first 5000 chars) ===")
print(r.text[:5000])

# Look for PDF URLs
print(f"\n=== PDF URLs ===")
pdf_urls = re.findall(r'(https?://[^"\\s]*\.pdf[^"\\s]*)', r.text)
for u in pdf_urls:
    print(f"  {u}")

# Look for file/document references
print(f"\n=== File/doc references ===")
for pattern in [r'"url":"([^"]+)"', r'"file":\{[^}]+\}', r'"title":"([^"]+)"', r'"uid":"([^"]+)"']:
    matches = re.findall(pattern, r.text)
    for m in matches[:10]:
        print(f"  {m[:200]}")

# Try to extract JSON objects from RSC format
print(f"\n=== JSON objects in RSC ===")
# RSC format has lines like "0:..." where the data follows
for line in r.text.split('\n'):
    if '{' in line and ('pdf' in line.lower() or 'title' in line.lower() or 'url' in line.lower() or 'file' in line.lower()):
        print(f"  {line[:500]}")
