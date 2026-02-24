"""Tata Mutual Fund factsheet spider.

Tata MF factsheet PDF links are directly in the server-rendered HTML
on betacms.tatamutualfund.com CDN. We look for "TataMF Factsheet" PDF.
"""
import scrapy
import os
import re
from urllib.parse import unquote
from scrapy_factsheets.items import FactsheetItem


class TataMFSpider(scrapy.Spider):
    name = "tata_mf"
    allowed_domains = ["www.tatamutualfund.com", "betacms.tatamutualfund.com", "betacmsadmin.tatamutualfund.com"]
    start_urls = ["https://www.tatamutualfund.com/information-documents/factsheets"]

    def parse(self, response):
        # Find TataMF Factsheet PDF link in the page HTML
        # Pattern: betacms.tatamutualfund.com/system/files/.../TataMF Factsheet-....pdf
        all_urls = re.findall(
            r'https?://betacms(?:admin)?\.tatamutualfund\.com/system/files/[^"\'\\]+\.pdf',
            response.text
        )

        factsheet_urls = [
            u for u in all_urls
            if "Factsheet" in unquote(u) or "factsheet" in unquote(u).lower()
        ]

        if not factsheet_urls:
            self.logger.error("No factsheet PDF found on page")
            return

        # Remove duplicates, take first (latest)
        seen = set()
        unique = []
        for u in factsheet_urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)

        pdf_url = unique[0]
        self.logger.info(f"Found factsheet: {unquote(pdf_url)}")

        # Extract title from filename
        filename = unquote(pdf_url.split("/")[-1]).replace(".pdf", "")
        title = filename.strip()

        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={"title": title},
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "tata-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "tata-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
