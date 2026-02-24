"""Bandhan Mutual Fund factsheet spider.

Bandhan MF is a React SPA backed by WordPress at cmsnew.bandhanmutual.com.
The factsheet API returns yearly items, each containing disclosure_files
with PDF links hosted on Google Cloud Storage.

API: /wp-json/finance-api/v1/posts/monthly-factsheets?bypass_pagination=true
"""
import scrapy
import json
import re
from scrapy_factsheets.items import FactsheetItem


class BandhanMFSpider(scrapy.Spider):
    name = "bandhan_mf"
    allowed_domains = ["cmsnew.bandhanmutual.com", "storage.googleapis.com"]

    API_URL = (
        "https://cmsnew.bandhanmutual.com/wp-json/finance-api/v1/posts/"
        "monthly-factsheets?bypass_pagination=true"
    )

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json",
            "Origin": "https://bandhanmutual.com",
            "Referer": "https://bandhanmutual.com/",
        },
    }

    def start_requests(self):
        yield scrapy.Request(self.API_URL, callback=self.parse)

    def parse(self, response):
        data = json.loads(response.text)
        items = data.get("data", [])

        if not items:
            self.logger.error("No factsheet data returned from API")
            return

        # First item is the latest year
        latest = items[0]
        year = latest.get("acf_fields", {}).get("financial_year", "")
        self.logger.info(f"Latest year: {year}")

        files = latest.get("acf_fields", {}).get("disclosure_files", [])
        self.logger.info(f"Disclosure files: {len(files)}")

        if not files:
            self.logger.error("No disclosure files found")
            return

        # Log all available files
        for f in files:
            name = f.get("document_name", "")
            link = f.get("document_link", {})
            url = link.get("url", "") if isinstance(link, dict) else ""
            self.logger.info(f"  File: {name} -> {url[:80]}...")

        # Find the latest non-passive factsheet
        # Main factsheets are named like "February 2026" (no 'factsheet' keyword)
        # Passive ones are "Passive Factsheet - February 2026"
        target_file = None
        for f in files:
            name = f.get("document_name", "").lower()
            if "passive" not in name:
                target_file = f
                break

        # Last resort: first file
        if not target_file:
            target_file = files[0]

        doc_name = target_file.get("document_name", "Bandhan Factsheet")
        doc_link = target_file.get("document_link", {})
        pdf_url = doc_link.get("url", "") if isinstance(doc_link, dict) else ""

        if not pdf_url:
            self.logger.error(f"No PDF URL in document: {doc_name}")
            return

        self.logger.info(f"Selected: {doc_name}")
        self.logger.info(f"PDF URL: {pdf_url}")

        item = FactsheetItem()
        item["fund_name"] = "bandhan-mf"
        item["file_urls"] = [pdf_url]
        item["factsheet_label"] = doc_name
        yield item
