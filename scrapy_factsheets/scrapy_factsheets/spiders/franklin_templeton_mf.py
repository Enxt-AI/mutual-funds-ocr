"""Franklin Templeton India factsheet spider.

Franklin Templeton uses a literature API backed by BloomReach CMS.
API: /api/literature/v1/documents?channel=en-in&contentGrouping=FUND-FACTSHEETS
Returns JSON with sorted list of factsheet documents (newest first).
Each document has a direct `downloadUrl` pointing to Widen CDN.
"""
import scrapy
import json
import os
from scrapy_factsheets.items import FactsheetItem


class FranklinTempletonMFSpider(scrapy.Spider):
    name = "franklin_templeton_mf"
    allowed_domains = ["www.franklintempletonindia.com", "franklintempletonprod.widen.net"]

    API_URL = (
        "https://www.franklintempletonindia.com"
        "/api/literature/v1/documents"
        "?channel=en-in&contentGrouping=FUND-FACTSHEETS"
    )

    def start_requests(self):
        yield scrapy.Request(
            self.API_URL,
            headers={"Accept": "application/json"},
        )

    def parse(self, response):
        data = json.loads(response.text)
        docs = data.get("document", [])

        if not docs:
            self.logger.error("No factsheet documents in API response")
            return

        # Filter to only Factsheet type documents
        factsheets = [d for d in docs if d.get("dctermsType") == "Factsheet"]
        self.logger.info(f"Found {len(factsheets)} factsheet(s)")

        if not factsheets:
            self.logger.error("No Factsheet-type documents found")
            return

        # First item is the latest (sorted by date)
        latest = factsheets[0]
        title = latest.get("dctermsTitle", "")
        pdf_url = latest.get("downloadUrl", "")

        if not pdf_url:
            self.logger.error("No downloadUrl in latest factsheet")
            return

        self.logger.info(f"Latest: {title}")
        self.logger.info(f"PDF URL: {pdf_url}")

        # Download directly from Widen CDN — no redirect issues
        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={"title": title},
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"Failed to download PDF: status {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "franklin-templeton-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        # Extract clean filename from URL
        filename = response.url.split("/")[-1].split("?")[0]
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "franklin-templeton-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
