"""Quantum AMC mutual fund factsheet spider.

Quantum AMC factsheet page has direct PDF links in server-rendered HTML.
PDFs served via /FileCDN/FactSheet/{guid}.pdf with GUID-based filenames.
The latest factsheet appears first on the page.
"""
import scrapy
import os
from scrapy_factsheets.items import FactsheetItem


class QuantumAMCSpider(scrapy.Spider):
    name = "quantum_amc"
    allowed_domains = ["www.quantumamc.com"]
    start_urls = ["https://www.quantumamc.com/factsheets/combined/-1/0/0"]

    def parse(self, response):
        # Find factsheet PDF links from CDN
        links = response.css('a[href*="FileCDN/FactSheet"]')
        
        if not links:
            self.logger.error("No factsheet links found!")
            return

        # Get the first (latest) link
        first_link = links[0]
        href = first_link.attrib.get("href", "")
        text = first_link.css("::text").get("").strip()
        
        pdf_url = response.urljoin(href)
        title = f"Quantum AMC Factsheet - {text}" if text else "Quantum AMC Factsheet"

        self.logger.info(f"Found {len(links)} factsheet link(s)")
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
            r"d:\OCR\OCR\Scraped Factsheets", "quantum-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "quantum-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
