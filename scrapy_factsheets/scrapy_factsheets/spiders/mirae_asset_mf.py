"""Mirae Asset Mutual Fund factsheet spider.

Mirae Asset MF uses a simple JSON API:
  POST /AjaxService/GetFactsheetDownload
  Body: {"navAnchorId": "nav-fact-tab1"}
  Response: {"Data": [{"Title": "...", "URL": "/docs/...", "PublishDate": ...}]}

Downloads both Active and Passive factsheets (latest month).
"""
import scrapy
import json
import os
from scrapy_factsheets.items import FactsheetItem


class MiraeAssetMFSpider(scrapy.Spider):
    name = "mirae_asset_mf"
    allowed_domains = ["www.miraeassetmf.co.in", "miraeassetmf.co.in"]

    API_URL = "https://www.miraeassetmf.co.in/AjaxService/GetFactsheetDownload"
    BASE_URL = "https://www.miraeassetmf.co.in"

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "https://www.miraeassetmf.co.in",
            "Referer": "https://www.miraeassetmf.co.in/downloads/factsheet",
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            self.API_URL,
            method="POST",
            body=json.dumps({"navAnchorId": "nav-fact-tab1"}),
            callback=self.parse_api,
            dont_filter=True,
        )

    def parse_api(self, response):
        data = json.loads(response.text)
        items = data.get("Data", [])

        self.logger.info(f"Found {len(items)} factsheet(s)")

        if not items:
            self.logger.error("No factsheets returned")
            return

        # Only download the latest factsheets (first 2: Active + Passive)
        for item in items[:2]:
            title = item.get("Title", "")
            url_path = item.get("URL", "")

            if not url_path:
                continue

            pdf_url = f"{self.BASE_URL}{url_path}"
            self.logger.info(f"Downloading: {title} -> {pdf_url}")

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
            r"d:\OCR\OCR\Scraped Factsheets", "mirae-asset-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "mirae-asset-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
