"""Shriram AMC mutual fund factsheet spider.

Shriram AMC factsheet page has direct PDF links in server-rendered HTML.
PDFs hosted on CDN at cdn.shriramamc.in/uploads/fact-sheet/
The latest factsheet appears first on the page.
Pattern: SAMC-Factsheet-(Full)-{Month}-{Year}.pdf
"""
import scrapy
import os
import re
from scrapy_factsheets.items import FactsheetItem


class ShriramAMCSpider(scrapy.Spider):
    name = "shriram_amc"
    allowed_domains = ["www.shriramamc.in", "cdn.shriramamc.in"]
    start_urls = ["https://www.shriramamc.in/factsheet"]

    def parse(self, response):
        # Find factsheet PDF links from CDN
        pdf_links = response.css('a[href*="cdn.shriramamc.in"][href$=".pdf"]::attr(href)').getall()

        if not pdf_links:
            self.logger.error("No factsheet PDF links found!")
            return

        self.logger.info(f"Found {len(pdf_links)} factsheet PDF(s)")

        # First link is the latest
        pdf_url = pdf_links[0]
        
        # Extract month/year from filename
        # e.g. SAMC-Factsheet-(Full)-Jan-2026.pdf
        filename = pdf_url.split("/")[-1]
        clean = filename.replace(".pdf", "").replace("SAMC-", "Shriram ").replace("-(Full)", "").replace("-", " ")
        title = clean.strip()

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
            r"d:\OCR\OCR\Scraped Factsheets", "shriram-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "shriram-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
