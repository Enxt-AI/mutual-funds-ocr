"""Zerodha Fund House factsheet spider.

Zerodha Fund House uses a separate API at api.zerodhafundhouse.com.
The /api/v1/reports endpoint returns all document categories including
factsheets. Each category has an id, title, and files array.
The 'factsheet' category contains monthly combined factsheet PDFs
hosted on assets.zerodhafundhouse.com.
"""
import json
import scrapy
import os
from urllib.parse import quote
from scrapy_factsheets.items import FactsheetItem


class ZerodhaFundHouseSpider(scrapy.Spider):
    name = "zerodha_fund_house"
    allowed_domains = [
        "api.zerodhafundhouse.com",
        "assets.zerodhafundhouse.com",
    ]

    API_URL = "https://api.zerodhafundhouse.com/api/v1/reports"

    def start_requests(self):
        yield scrapy.Request(
            self.API_URL,
            callback=self.parse_reports,
            dont_filter=True,
        )

    def parse_reports(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"JSON parse error: {response.text[:200]}")
            return

        categories = data.get("data", [])
        if not categories:
            self.logger.warning("No categories returned from API")
            return

        # Find the factsheet category
        factsheet_cat = None
        for cat in categories:
            if cat.get("id") == "factsheet":
                factsheet_cat = cat
                break

        if not factsheet_cat:
            self.logger.warning("No 'factsheet' category found")
            return

        files = factsheet_cat.get("files", [])
        self.logger.info(f"Found {len(files)} factsheet files")

        if not files:
            self.logger.warning("No factsheet files in category")
            return

        # Files are sorted by date desc; take the first (latest)
        latest = files[0]
        title = latest.get("name", "Zerodha Factsheet")
        pdf_url = latest.get("url", "")

        if not pdf_url:
            self.logger.error("No URL for latest factsheet")
            return

        self.logger.info(f"Latest factsheet: {title} -> {pdf_url}")

        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={"title": title},
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "zerodha-fund-house"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "zerodha-fund-house"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
