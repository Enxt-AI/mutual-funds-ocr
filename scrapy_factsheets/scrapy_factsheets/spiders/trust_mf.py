"""Trust Mutual Fund factsheet spider.

Trust MF uses a WordPress backend with REST API.
Factsheets are available as media items at:
  /trustmfsys/wp-json/wp/v2/media?search=factsheet&per_page=5
Filter for PDF files and pick the latest one.
"""
import scrapy
import json
import os
import re
from scrapy_factsheets.items import FactsheetItem


class TrustMFSpider(scrapy.Spider):
    name = "trust_mf"
    allowed_domains = ["www.trustmf.com", "trustmf.com"]

    WP_API = (
        "https://www.trustmf.com/trustmfsys/wp-json/wp/v2/media"
        "?search=factsheet&per_page=10&orderby=date&order=desc"
    )

    def start_requests(self):
        yield scrapy.Request(self.WP_API, callback=self.parse_api)

    def parse_api(self, response):
        try:
            items = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Failed to parse API response: {e}")
            return

        # Find the latest PDF factsheet (not xlsx)
        for item in items:
            source_url = item.get("source_url", "")
            title = item.get("title", {}).get("rendered", "")
            mime = item.get("mime_type", "")

            if mime == "application/pdf" and "factsheet" in title.lower():
                clean_title = re.sub(r'&#\d+;', '-', title).strip(' -')
                self.logger.info(f"Found: {clean_title} -> {source_url}")

                yield scrapy.Request(
                    source_url,
                    callback=self.save_pdf,
                    meta={"title": clean_title},
                    dont_filter=True,
                )
                return

        self.logger.error("No factsheet PDF found in API response")

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "trust-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "trust-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
