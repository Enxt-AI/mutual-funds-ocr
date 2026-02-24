"""Baroda BNP Paribas Mutual Fund factsheet spider.

The downloads page is server-rendered and shows the latest factsheet
with a direct PDF download link at:
/assets/download_documents/Factsheet-{Month}_{Year}_{id}.pdf
"""
import scrapy
import re
from scrapy_factsheets.items import FactsheetItem


class BarodaBNPSpider(scrapy.Spider):
    name = "baroda_bnp"
    allowed_domains = ["www.barodabnpparibasmf.in"]
    start_urls = [
        "https://www.barodabnpparibasmf.in/downloads/monthly-factsheet"
    ]

    def parse(self, response):
        # Find all PDF links in the download_documents directory
        pdf_links = response.css(
            'a[href*="download_documents"][href$=".pdf"]::attr(href)'
        ).getall()

        if not pdf_links:
            # Fallback: broader PDF search
            pdf_links = response.css(
                'a[href*="Factsheet"][href$=".pdf"]::attr(href)'
            ).getall()

        if not pdf_links:
            self.logger.error("No factsheet PDF links found")
            return

        # Deduplicate while preserving order
        seen = set()
        unique_links = []
        for link in pdf_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        self.logger.info(f"Found {len(unique_links)} unique PDF link(s)")

        # Take the first unique PDF (the latest factsheet)
        pdf_url = response.urljoin(unique_links[0])
        self.logger.info(f"PDF URL: {pdf_url}")

        # Extract label from filename
        filename = unique_links[0].split("/")[-1]
        # "Factsheet-January_2026_16627.pdf" -> "Factsheet January 2026"
        label = re.sub(r'_\d+\.pdf$', '', filename)
        label = label.replace('-', ' ').replace('_', ' ')

        self.logger.info(f"Label: {label}")

        item = FactsheetItem()
        item["fund_name"] = "baroda-bnp-paribas"
        item["file_urls"] = [pdf_url]
        item["factsheet_label"] = label
        yield item
