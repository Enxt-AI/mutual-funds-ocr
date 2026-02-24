"""Kotak Mutual Fund factsheet spider.

Kotak MF hosts factsheets on S3/CloudFront with a predictable URL pattern:
  https://vatseelabs-s3.kotakmf.com/FormsDownloads/Factsheet/
    Factsheet-for-{Month}-{Year}/KotakMFFactsheet{Month}{Year}.pdf

Example:
  Factsheet-for-January-2026/KotakMFFactsheetJanuary2026.pdf
"""
import scrapy
import os
from datetime import datetime, timedelta
from scrapy_factsheets.items import FactsheetItem


class KotakMFSpider(scrapy.Spider):
    name = "kotak_mf"
    allowed_domains = ["vatseelabs-s3.kotakmf.com"]

    BASE = "https://vatseelabs-s3.kotakmf.com/FormsDownloads/Factsheet"

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    def start_requests(self):
        """Try most recent month first, chain to older months on failure."""
        yield self._request_for_offset(0)

    def _request_for_offset(self, offset):
        now = datetime.now()
        dt = now - timedelta(days=30 * offset)
        month_name = self.MONTHS[dt.month - 1]
        year = dt.year

        url = (
            f"{self.BASE}/Factsheet-for-{month_name}-{year}/"
            f"KotakMFFactsheet{month_name}{year}.pdf"
        )

        self.logger.info(f"Trying: {month_name} {year}")
        return scrapy.Request(
            url,
            callback=self.save_pdf,
            errback=self.handle_error,
            meta={"offset": offset, "month": month_name, "year": year},
            dont_filter=True,
        )

    def handle_error(self, failure):
        offset = failure.request.meta.get("offset", 0)
        month = failure.request.meta.get("month", "")
        year = failure.request.meta.get("year", "")
        self.logger.warning(f"Failed for {month} {year}: {failure.value}")
        if offset < 3:
            yield self._request_for_offset(offset + 1)

    def save_pdf(self, response):
        offset = response.meta["offset"]
        month = response.meta["month"]
        year = response.meta["year"]

        if response.status != 200 or len(response.body) < 10000:
            self.logger.info(f"No factsheet for {month} {year} (status={response.status})")
            if offset < 3:
                yield self._request_for_offset(offset + 1)
            return

        title = f"Kotak MF Factsheet {month} {year}"
        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "kotak-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"KotakMFFactsheet{month}{year}.pdf"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "kotak-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
