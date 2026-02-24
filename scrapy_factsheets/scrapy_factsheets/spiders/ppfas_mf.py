"""PPFAS Mutual Fund factsheet spider.

PPFAS MF factsheet page has direct PDF links in server-rendered HTML.
Pattern: /downloads/factsheet/{year}/ppfas-mf-factsheet-for-{Month}-{year}.pdf
The latest factsheet link appears first under the 2026 section.
"""
import scrapy
import os
from scrapy_factsheets.items import FactsheetItem


class PPFASMFSpider(scrapy.Spider):
    name = "ppfas_mf"
    allowed_domains = ["amc.ppfas.com"]
    start_urls = ["https://amc.ppfas.com/downloads/factsheet/index.php"]

    def parse(self, response):
        # Find factsheet PDF links
        pdf_links = response.css('a[href$=".pdf"]::attr(href), a[href*=".pdf?"]::attr(href)').getall()
        factsheet_pdfs = [l for l in pdf_links if "factsheet" in l.lower()]

        self.logger.info(f"Found {len(factsheet_pdfs)} factsheet PDF(s)")

        if not factsheet_pdfs:
            self.logger.error("No factsheet PDF links found!")
            return

        # Get the first (latest) factsheet
        pdf_url = response.urljoin(factsheet_pdfs[0])
        
        # Extract month/year from URL for the label
        # e.g. ppfas-mf-factsheet-for-January-2026.pdf
        filename = factsheet_pdfs[0].split("/")[-1].split("?")[0]
        title = f"PPFAS MF Factsheet - {filename.replace('.pdf', '').replace('ppfas-mf-factsheet-for-', '')}"

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
            r"d:\OCR\OCR\Scraped Factsheets", "ppfas-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "ppfas-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
