"""Invesco Mutual Fund factsheet spider.

Invesco MF exposes a JSON API at:
  https://www.invescomutualfund.com/api/RequestForLiterature?year=0
which returns all documents. The response is a list with one element
containing a `Factsheet` array. Each entry has:
  - DocumentName:  "Factsheet - January 2026"
  - DocumentUrl:   direct PDF link
  - DocumentDate:  "1/11/2026 6:30:00 PM"
  - Year:          "2026"

The first entry in the Factsheet array is the latest.
"""
import scrapy
import json
import os
from urllib.parse import unquote
from scrapy_factsheets.items import FactsheetItem


class InvescoMFSpider(scrapy.Spider):
    name = "invesco_mf"
    allowed_domains = ["www.invescomutualfund.com", "invescomutualfund.com"]
    start_urls = [
        "https://www.invescomutualfund.com/api/RequestForLiterature?year=0"
    ]

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json",
            "Referer": "https://invescomutualfund.com/literature-and-form?tab=Factsheets",
        },
    }

    def parse(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON response")
            return

        if not data or not isinstance(data, list):
            self.logger.error("Unexpected response format")
            return

        factsheets = data[0].get("Factsheet", [])
        if not factsheets:
            self.logger.error("No factsheets found in API response")
            return

        self.logger.info(f"Found {len(factsheets)} factsheet(s)")

        # First entry is the latest
        latest = factsheets[0]
        name = latest.get("DocumentName", "")
        url = latest.get("DocumentUrl", "")
        date = latest.get("DocumentDate", "")

        if not url:
            self.logger.error("Latest factsheet has no URL")
            return

        self.logger.info(f"Latest: {name} ({date})")
        self.logger.info(f"PDF URL: {url}")

        yield scrapy.Request(
            url,
            callback=self.save_pdf,
            meta={"title": name},
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"Failed to download PDF: status {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "invesco-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = unquote(response.url.split("/")[-1]).split("?")[0]
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "invesco-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
