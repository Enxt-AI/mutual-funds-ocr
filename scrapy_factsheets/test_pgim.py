"""Use Playwright with stealth to intercept PGIM India factsheet download."""
from playwright.sync_api import sync_playwright
import time
import os

download_urls = []
api_calls = []

def handle_response(response):
    ct = response.headers.get('content-type', '')
    url = response.url
    if 'pdf' in ct or '.pdf' in url:
        print(f"  PDF RESPONSE: {response.status} {url}")
        download_urls.append(url)
    if 'api' in url and 'google' not in url:
        print(f"  API RESPONSE: {response.status} {url} CT={ct}")
        try:
            body = response.text()
            if body and len(body) > 2:
                api_calls.append((url, body[:500]))
                print(f"    Body: {body[:200]}")
        except:
            pass

def handle_request(request):
    url = request.url
    if ('api' in url or 'download' in url) and 'google' not in url and 'ux4g' not in url:
        print(f"  REQUEST: {request.method} {url}")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,  # Use headed mode to avoid detection
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
        ]
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
    )
    
    # Remove webdriver flag
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
    """)
    
    page = context.new_page()
    page.on("response", handle_response)
    page.on("request", handle_request)
    
    print("Loading PGIM India factsheet page...")
    page.goto("https://www.pgimindia.com/mutual-funds/forms-and-product-updates/Fund-Factsheet", 
              wait_until="networkidle", timeout=60000)
    print(f"Page loaded. Title: {page.title()}")
    
    time.sleep(5)
    
    # Find the factsheet card
    card = page.locator("text=Factsheet - January 2026").first
    if card.is_visible():
        print(f"\nFound card: {card.inner_text()}")
        
        # Click and monitor what happens
        print("Clicking...")
        
        # Try with download handler
        try:
            with page.expect_download(timeout=15000) as download_info:
                card.click()
            download = download_info.value
            print(f"\nDownload triggered!")
            print(f"  URL: {download.url}")
            print(f"  Filename: {download.suggested_filename}")
            
            save_dir = r"d:\OCR\OCR\Scraped Factsheets\pgim-india-mutual-fund"
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, download.suggested_filename)
            download.save_as(filepath)
            print(f"  Saved to: {filepath} ({os.path.getsize(filepath)} bytes)")
        except Exception as e:
            print(f"No download dialog: {e}")
            # Maybe it opens in a new tab
            time.sleep(3)
            pages = context.pages
            print(f"Pages after click: {len(pages)}")
            for pg in pages:
                print(f"  Page: {pg.url}")
    else:
        print("Card not visible")
        # Take screenshot
        page.screenshot(path="pgim_page.png")
        print("Screenshot saved to pgim_page.png")
        
        # Check all visible elements
        titles = page.locator(".file-title").all()
        print(f"File titles: {len(titles)}")
        for t in titles:
            try:
                print(f"  - {t.inner_text()}")
            except:
                pass
    
    print(f"\nCaptured API calls: {len(api_calls)}")
    for url, body in api_calls:
        print(f"  {url}: {body[:200]}")
    
    print(f"Download URLs: {download_urls}")
    browser.close()
