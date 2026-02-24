"""Groww Mutual Fund factsheet spider.

Groww MF serves factsheet PDFs directly from static storage at
assets-netstorage.growwmf.in. The download page lists all factsheets as
<a> links with .pdf extensions. We parse dates from titles to find the latest.
"""
import scrapy
import re
import os
from datetime import datetime
from scrapy_factsheets.items import FactsheetItem


class GrowwMFSpider(scrapy.Spider):
    name = "groww_mf"
    allowed_domains = ["www.growwmf.in", "assets-netstorage.growwmf.in"]
    start_urls = ["https://www.growwmf.in/downloads/fact-sheet"]

    # Month abbreviations and full names for date parsing
    MONTHS = {
        "jan": 1, "january": 1, "feb": 2, "february": 2,
        "mar": 3, "march": 3, "apr": 4, "april": 4,
        "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    def parse_date_from_title(self, title):
        """Extract a (year, month) tuple from a factsheet title."""
        title_lower = title.lower()
        month = None
        year = None

        for name, num in self.MONTHS.items():
            if name in title_lower:
                month = num
                break

        # Find year: 2-digit or 4-digit
        year_match = re.search(r'(20\d{2})', title)
        if year_match:
            year = int(year_match.group(1))
        else:
            # Try 2-digit year like "Jan 26" or "Dec 25"
            year2_match = re.search(r'[\s-](\d{2})(?:\.pdf)?$', title.strip())
            if year2_match:
                y = int(year2_match.group(1))
                year = 2000 + y

        if month and year:
            return (year, month)
        return (0, 0)

    def parse(self, response):
        # Find all PDF links containing "Factsheet"
        links = response.css('a[href*=".pdf"]')
        factsheets = []

        for link in links:
            href = link.attrib.get("href", "")
            text = link.css("::text").get("").strip()

            if "factsheet" in text.lower() or "factsheet" in href.lower():
                date_tuple = self.parse_date_from_title(text or href)
                factsheets.append({
                    "title": text,
                    "url": response.urljoin(href),
                    "date": date_tuple,
                })

        if not factsheets:
            self.logger.error("No factsheet links found")
            return

        self.logger.info(f"Found {len(factsheets)} factsheet(s)")

        # Sort by date descending to get the latest
        factsheets.sort(key=lambda x: x["date"], reverse=True)
        latest = factsheets[0]

        self.logger.info(f"Latest: {latest['title']}")
        self.logger.info(f"PDF URL: {latest['url']}")

        yield scrapy.Request(
            latest["url"],
            callback=self.save_pdf,
            meta={"title": latest["title"]},
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"Failed to download PDF: status {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "groww-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = response.url.split("/")[-1]
        # URL-decode the filename
        from urllib.parse import unquote
        filename = unquote(filename)
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "groww-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
