"""
Quick test script to check if the Aditya Birla factsheet page can be fetched
with proper browser headers, and find the factsheet download links/API.
"""
import requests
from bs4 import BeautifulSoup
import json
import re

# Full browser-like headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

url = "https://mutualfund.adityabirlacapital.com/forms-and-downloads/factsheets"

print(f"Fetching: {url}")
try:
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"Content length: {len(resp.text)} chars")
    
    # Look for PDF links
    pdf_links = re.findall(r'https?://[^\s"\'<>]+\.pdf', resp.text)
    if pdf_links:
        print(f"\nFound {len(pdf_links)} PDF links:")
        for link in pdf_links[:10]:
            print(f"  {link}")
    else:
        print("\nNo direct PDF links found in HTML.")
    
    # Look for API endpoints in the JavaScript
    api_patterns = re.findall(r'["\'](/api/[^"\']+)["\']', resp.text)
    if api_patterns:
        print(f"\nFound {len(api_patterns)} API endpoints:")
        for api in set(api_patterns):
            print(f"  {api}")
    
    # Look for XHR/fetch patterns
    xhr_patterns = re.findall(r'fetch\(["\']([^"\']+)["\']', resp.text)
    if xhr_patterns:
        print(f"\nFound {len(xhr_patterns)} fetch() calls:")
        for xhr in xhr_patterns[:10]:
            print(f"  {xhr}")
    
    # Save for inspection
    with open("absl_page.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    print("\nSaved full HTML to absl_page.html for inspection.")
    
except Exception as e:
    print(f"Error: {e}")
