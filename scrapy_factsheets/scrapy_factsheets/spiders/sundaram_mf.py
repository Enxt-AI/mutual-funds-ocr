"""Sundaram Mutual Fund factsheet spider.

Sundaram MF consolidated factsheet is fetched via ASP.NET AJAX proxy:
  POST /ajax/...ashx?_method=DownloadArchive&_session=no
  Body: cat=1\\r\\nmnth=MM/YYYY
  Returns: PDF URL string or 'Not Available'
Downloads only the latest available consolidated factsheet.
"""
import scrapy
import os
from datetime import datetime, timedelta
from scrapy_factsheets.items import FactsheetItem


class SundaramMFSpider(scrapy.Spider):
    name = "sundaram_mf"
    allowed_domains = ["www.sundarammutual.com"]

    API_URL = "https://www.sundarammutual.com/ajax/Modules_Forms_Downloads_Fundwise_Factsheet,App_Web_iwjfkxgb.ashx?_method=DownloadArchive&_session=no"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found = False

    def start_requests(self):
        # Start with current month
        yield self._make_request(0)

    def _make_request(self, offset):
        dt = datetime.now() - timedelta(days=30 * offset)
        month_str = f"{dt.month:02d}/{dt.year}"
        return scrapy.Request(
            self.API_URL,
            method="POST",
            headers={
                "Referer": "https://www.sundarammutual.com/fundwise-factsheet",
            },
            body=f"cat=1\r\nmnth={month_str}",
            callback=self.parse_api,
            meta={"month_str": month_str, "offset": offset},
            dont_filter=True,
        )

    def parse_api(self, response):
        if self.found:
            return

        body = response.text.strip().strip("'\"")
        month_str = response.meta["month_str"]
        offset = response.meta["offset"]

        if body == "Not Available" or body == "Exception" or not body.startswith("http"):
            self.logger.info(f"No factsheet for {month_str}, trying previous month...")
            if offset < 6:
                yield self._make_request(offset + 1)
            return

        self.found = True
        pdf_url = body
        title = f"Sundaram MF Consolidated Factsheet {month_str.replace('/', '-')}"
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
            r"d:\OCR\OCR\Scraped Factsheets", "sundaram-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "sundaram-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
