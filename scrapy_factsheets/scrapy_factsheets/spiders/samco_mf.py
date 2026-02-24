"""Samco Mutual Fund factsheet spider.

Samco MF downloads page has direct PDF links in server-rendered HTML.
PDFs hosted at media1.samco.in/scomamc/amc_documents/ and also downloadable
via /amc-document-download/ path. The latest factsheet in the 2025-26 section
appears first in the list.
"""
import scrapy
import os
import re
from scrapy_factsheets.items import FactsheetItem


class SamcoMFSpider(scrapy.Spider):
    name = "samco_mf"
    allowed_domains = ["www.samcomf.com"]
    start_urls = ["https://www.samcomf.com/downloads"]

    def parse(self, response):
        # Find all factsheet PDF links via amc-document-download path
        all_links = response.css('a[href*="amc-document-download"]::attr(href)').getall()
        factsheet_links = [l for l in all_links if "factsheet" in l.lower() or "Factsheet" in l]

        self.logger.info(f"Found {len(factsheet_links)} factsheet link(s)")

        if not factsheet_links:
            self.logger.error("No factsheet links found!")
            return

        # Find the most recent factsheet by searching for the latest year
        from datetime import datetime
        current_year = datetime.now().year
        latest_link = None
        for year in range(current_year, current_year - 3, -1):
            year_links = [l for l in factsheet_links if str(year) in l]
            if year_links:
                latest_link = year_links[0]  # First in year section = most recent month
                break

        if not latest_link:
            latest_link = factsheet_links[0]

        pdf_url = response.urljoin(latest_link)

        # Extract label from filename
        filename = latest_link.split("/")[-1]
        # e.g. Factsheet-January2026_1769959976.pdf
        # Remove timestamp and extension
        clean = re.sub(r'_\d+\.pdf$', '', filename)
        clean = re.sub(r'SamcoMutualFund', '', clean)
        clean = re.sub(r'[-_]', ' ', clean).strip()
        title = f"Samco MF {clean}"

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
            r"d:\OCR\OCR\Scraped Factsheets", "samco-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "samco-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
