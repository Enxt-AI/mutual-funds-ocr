"""LIC Mutual Fund factsheet spider.

LIC MF factsheet page is server-rendered HTML with direct PDF links.
The "current" section contains factsheet links like:
  /assets/downloads/monthly_fact_sheet/2025-2026/02/lic-mf-factsheet-....pdf

Note: Site has SSL certificate issues, so we disable certificate verification.
"""
import scrapy
import os
import re
from scrapy_factsheets.items import FactsheetItem


class LicMFSpider(scrapy.Spider):
    name = "lic_mf"
    allowed_domains = ["www.licmf.com", "licmf.com"]
    start_urls = ["https://www.licmf.com/downloads/factsheet"]

    custom_settings = {
        # Disable SSL verification for LIC MF (cert issues)
        "DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING": True,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"download_verify_ssl": False},
                dont_filter=True,
            )

    def parse(self, response):
        # Find the first factsheet PDF link in the "current" section
        current_div = response.css("div#current")
        if not current_div:
            current_div = response  # fallback to full page

        pdf_links = current_div.css(
            'a[href*="monthly_fact_sheet"][href$=".pdf"]::attr(href)'
        ).getall()

        if not pdf_links:
            # Broader search
            pdf_links = response.css(
                'a[href*="factsheet"][href$=".pdf"]::attr(href)'
            ).getall()

        self.logger.info(f"Found {len(pdf_links)} factsheet PDF links")

        if not pdf_links:
            self.logger.error("No factsheet PDFs found!")
            return

        # Take the first (latest) factsheet
        pdf_path = pdf_links[0]
        pdf_url = response.urljoin(pdf_path)
        filename = pdf_path.split("/")[-1]

        self.logger.info(f"Latest factsheet: {pdf_url}")

        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={
                "title": filename,
                "download_verify_ssl": False,
            },
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "lic-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filepath = os.path.join(save_dir, title)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "lic-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title.replace(".pdf", "")
        yield item
