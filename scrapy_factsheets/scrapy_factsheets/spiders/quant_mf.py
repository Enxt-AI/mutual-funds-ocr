"""Quant Mutual Fund factsheet spider.

Quant MF factsheet page has direct PDF links in server-rendered HTML.
Pattern: ../Admin/Factsheet/quant_Factsheet_{Month}_{Year}.pdf
The latest factsheet appears first on the page.
"""
import scrapy
import os
from scrapy_factsheets.items import FactsheetItem


class QuantMFSpider(scrapy.Spider):
    name = "quant_mf"
    allowed_domains = ["quantmutual.com"]
    start_urls = ["https://quantmutual.com/downloads/factsheet"]

    def parse(self, response):
        # Find factsheet PDF links
        pdf_links = response.css('a[href*="Factsheet"][href$=".pdf"]::attr(href)').getall()

        self.logger.info(f"Found {len(pdf_links)} factsheet PDF(s)")

        if not pdf_links:
            self.logger.error("No factsheet PDF links found!")
            return

        # Get the first (latest) factsheet
        pdf_url = response.urljoin(pdf_links[0])

        # Extract label from filename: quant_Factsheet_February_2026.pdf
        filename = pdf_links[0].split("/")[-1].replace(".pdf", "")
        parts = filename.replace("quant_Factsheet_", "").replace("_", " ")
        title = f"Quant MF Factsheet - {parts}"

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
            r"d:\OCR\OCR\Scraped Factsheets", "quant-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "quant-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
