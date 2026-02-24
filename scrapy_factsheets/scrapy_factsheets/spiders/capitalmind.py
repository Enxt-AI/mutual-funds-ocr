"""Capitalmind Mutual Fund factsheet spider.

Simple static page with direct PDF download links.
PDFs are at /uploads/Capitalmind_Factsheet_{Month}{Year}_{hash}.pdf
"""
import scrapy
import re
from scrapy_factsheets.items import FactsheetItem


class CapitalmindSpider(scrapy.Spider):
    name = "capitalmind"
    allowed_domains = ["capitalmindmf.com"]
    start_urls = ["https://capitalmindmf.com/factsheet.html"]

    def parse(self, response):
        # Find all PDF download links
        pdf_links = response.css('a[href$=".pdf"]::attr(href)').getall()

        if not pdf_links:
            self.logger.error("No PDF links found")
            return

        # Deduplicate and resolve
        seen = set()
        unique_links = []
        for link in pdf_links:
            full_url = response.urljoin(link)
            if full_url not in seen:
                seen.add(full_url)
                unique_links.append(full_url)

        self.logger.info(f"Found {len(unique_links)} PDF link(s)")

        # The first PDF link is the latest factsheet
        pdf_url = unique_links[0]
        self.logger.info(f"Latest PDF: {pdf_url}")

        # Extract month label: find the heading that precedes the download link
        # Page structure: <h6>January 2026</h6> <a href="...pdf">Download</a>
        first_pdf_link = response.css('a[href$=".pdf"]')
        if first_pdf_link:
            # Walk up to find the preceding h6
            parent = first_pdf_link[0].xpath("ancestor::*[.//h6]")
            if parent:
                label = parent[-1].css("h6::text").get("").strip()
            else:
                label = "Capitalmind Factsheet"
        else:
            label = "Capitalmind Factsheet"

        # Fallback: extract from filename
        if not label or label.lower() in ["declaration", "disclaimer", ""]:
            filename = pdf_url.split("/")[-1]
            label = re.sub(r'_[a-f0-9]+\.pdf$', '', filename)
            label = label.replace('_', ' ')

        self.logger.info(f"Label: {label}")

        item = FactsheetItem()
        item["fund_name"] = "capitalmind"
        item["file_urls"] = [pdf_url]
        item["factsheet_label"] = label
        yield item
