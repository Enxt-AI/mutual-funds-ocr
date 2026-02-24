"""Mahindra Manulife Mutual Fund factsheet spider.

Mahindra Manulife MF downloads page is server-rendered HTML with direct PDF links.
Factsheet links contain "factsheet" in text and href ends with .pdf.
Example: uploads/download/6692d134-1a4b-47f2-bf8b-24f8efc49f12.pdf
"""
import scrapy
import os
import re
from scrapy_factsheets.items import FactsheetItem


class MahindraManulifeMFSpider(scrapy.Spider):
    name = "mahindra_manulife_mf"
    allowed_domains = ["www.mahindramanulife.com", "mahindramanulife.com"]
    start_urls = ["https://www.mahindramanulife.com/downloads"]

    def parse(self, response):
        # Find factsheet links by matching text containing "factsheet" and href ending with .pdf
        for link in response.css("a[href$='.pdf'], a[href$='.PDF']"):
            text = link.css("::text").get("").strip()
            href = link.attrib.get("href", "")

            if re.search(r"fund\s*factsheet|factsheet", text, re.IGNORECASE):
                pdf_url = response.urljoin(href)
                self.logger.info(f"Latest factsheet: {text} -> {pdf_url}")

                yield scrapy.Request(
                    pdf_url,
                    callback=self.save_pdf,
                    meta={"title": text},
                    dont_filter=True,
                )
                return  # Only download the first (latest) factsheet

        self.logger.error("No factsheet PDF found on page!")

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "mahindra-manulife-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "mahindra-manulife-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
