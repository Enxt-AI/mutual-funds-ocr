"""Nippon India Mutual Fund factsheet spider.

Nippon India MF factsheet page has direct PDF links in server-rendered HTML.
Pattern: /InvestorServices/FactSheets/Nippon-FS-{Mon}-{Year}.pdf
The latest factsheet link appears first on the page.
"""
import scrapy
import os
import re
from scrapy_factsheets.items import FactsheetItem


class NipponIndiaMFSpider(scrapy.Spider):
    name = "nippon_india_mf"
    allowed_domains = ["mf.nipponindiaim.com"]
    start_urls = [
        "https://mf.nipponindiaim.com/investor-service/downloads/factsheet-portfolio-and-other-disclosures"
    ]

    def parse(self, response):
        # Find the first factsheet PDF link (Nippon-FS-*.pdf)
        links = response.css('a[href*="FactSheets"]::attr(href)').getall()
        pdf_links = [l for l in links if l.lower().endswith('.pdf')]

        if not pdf_links:
            # Fallback: broader search
            pdf_links = re.findall(
                r'href="([^"]*FactSheets[^"]*\.pdf)"', response.text, re.IGNORECASE
            )

        self.logger.info(f"Found {len(pdf_links)} factsheet PDF(s)")

        if not pdf_links:
            self.logger.error("No factsheet PDF links found!")
            return

        # Download the latest (first) factsheet
        pdf_url = response.urljoin(pdf_links[0])
        self.logger.info(f"Latest factsheet: {pdf_url}")

        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={"pdf_url": pdf_url},
            dont_filter=True,
        )

    def save_pdf(self, response):
        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "nippon-india-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        # Extract filename from URL
        filename = response.url.split("/")[-1].split("?")[0]
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "nippon-india-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = filename.replace(".pdf", "")
        yield item
