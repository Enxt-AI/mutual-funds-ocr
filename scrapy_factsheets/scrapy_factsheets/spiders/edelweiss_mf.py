"""Edelweiss Mutual Fund factsheet spider.

The Edelweiss MF site uses Akamai CDN which may temporarily block IPs after
repeated requests. We use the requests library with a proper session and
retry logic. The direct PDF URL is not blocked even during IP blocks.
"""
import scrapy
import requests as req_lib
import re
import os
import time
from urllib.parse import unquote
from scrapy_factsheets.items import FactsheetItem


class EdelweissMFSpider(scrapy.Spider):
    name = "edelweiss_mf"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
    }

    def start_requests(self):
        yield scrapy.Request(
            "https://httpbin.org/status/200",
            callback=self.do_work,
            dont_filter=True,
        )

    def do_work(self, response):
        """Use requests lib to fetch and download the factsheet."""
        session = req_lib.Session()
        session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })

        url = "https://www.edelweissmf.com/downloads/factsheets"
        self.logger.info(f"Fetching: {url}")

        # Retry up to 3 times with backoff
        resp = None
        for attempt in range(3):
            try:
                resp = session.get(url, timeout=15)
                if resp.status_code == 200:
                    break
                self.logger.warning(
                    f"Attempt {attempt+1}: status {resp.status_code}"
                )
                time.sleep(2 ** attempt)  # 1s, 2s, 4s backoff
            except Exception as e:
                self.logger.warning(f"Attempt {attempt+1}: {e}")
                time.sleep(2 ** attempt)

        if not resp or resp.status_code != 200:
            self.logger.error("Failed to fetch page after retries")
            return

        text = resp.text
        self.logger.info(f"Page size: {len(text)} chars")

        # Find factsheet PDF links
        pdf_links = re.findall(
            r'href=["\']([^"\']*\.pdf)["\']', text, re.IGNORECASE
        )
        factsheet_pdfs = [p for p in pdf_links if "factsheet" in p.lower()]

        if not factsheet_pdfs:
            self.logger.error("No factsheet PDFs found")
            return

        pdf_url = factsheet_pdfs[0]
        if not pdf_url.startswith("http"):
            pdf_url = f"https://www.edelweissmf.com{pdf_url}"

        # Extract label from filename
        filename = unquote(pdf_url.split("/")[-1])
        label_match = re.search(
            r"Factsheet\s+(\w+\s+\d{4})", filename, re.IGNORECASE
        )
        label = label_match.group(0) if label_match else filename

        self.logger.info(f"Selected: {label}")
        self.logger.info(f"PDF URL: {pdf_url}")

        # Download the PDF
        save_dir = os.path.join(r"d:\OCR\OCR\Scraped Factsheets", "edelweiss-mf")
        os.makedirs(save_dir, exist_ok=True)

        safe_filename = re.sub(r'[^\w\s\-.]', '', filename).strip()
        if not safe_filename:
            safe_filename = "edelweiss-factsheet.pdf"
        filepath = os.path.join(save_dir, safe_filename)

        self.logger.info("Downloading PDF...")
        pdf_resp = session.get(pdf_url, timeout=60)

        if pdf_resp.status_code == 200 and len(pdf_resp.content) > 1000:
            with open(filepath, "wb") as f:
                f.write(pdf_resp.content)
            self.logger.info(f"Saved: {filepath} ({len(pdf_resp.content)} bytes)")

            item = FactsheetItem()
            item["fund_name"] = "edelweiss-mf"
            item["file_urls"] = []
            item["files"] = [{"path": filepath, "url": pdf_url}]
            item["factsheet_label"] = label
            yield item
        else:
            self.logger.error(f"PDF download failed: {pdf_resp.status_code}")
