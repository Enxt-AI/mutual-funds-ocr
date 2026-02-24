"""NJ Mutual Fund factsheet spider.

NJ MF downloads page has direct factsheet PDF links in server-rendered HTML.
Links use viewfile.php?file=<filename>.pdf pattern.
The latest factsheet appears first under the "Factsheet" section.
"""
import scrapy
import os
import re
from scrapy_factsheets.items import FactsheetItem


class NJMFSpider(scrapy.Spider):
    name = "nj_mf"
    allowed_domains = ["downloads.njmutualfund.com"]
    start_urls = ["https://downloads.njmutualfund.com/downloads.php"]

    def parse(self, response):
        # Find links whose text explicitly contains "Factsheet"
        all_links = response.css('a[href*="viewfile.php"]')
        factsheet_links = []

        for link in all_links:
            href = link.attrib.get("href", "")
            text = link.css("::text").get("").strip()
            if "factsheet" in text.lower() and ".pdf" in href:
                factsheet_links.append((text, href))

        self.logger.info(f"Found {len(factsheet_links)} factsheet link(s)")

        if not factsheet_links:
            self.logger.error("No factsheet links found!")
            return

        # Download the latest (first) factsheet only
        title, href = factsheet_links[0]
        pdf_url = response.urljoin(href)
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
            r"d:\OCR\OCR\Scraped Factsheets", "nj-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "nj-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
