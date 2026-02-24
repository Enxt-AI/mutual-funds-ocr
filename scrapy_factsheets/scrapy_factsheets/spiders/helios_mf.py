"""Helios Mutual Fund factsheet spider.

Helios MF is a WordPress site with direct PDF links on the downloads page.
Factsheet links are tagged with "[FACTSHEET]" in the link text, or have
"Factsheet" in the URL. We filter for "Monthly Factsheets" section links
and parse dates to find the latest.
"""
import scrapy
import re
import os
from urllib.parse import unquote
from scrapy_factsheets.items import FactsheetItem


class HeliosMFSpider(scrapy.Spider):
    name = "helios_mf"
    allowed_domains = ["www.heliosmf.in", "heliosmf.in"]
    start_urls = ["https://www.heliosmf.in/downloads/"]

    MONTHS = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
        "oct": 10, "nov": 11, "dec": 12,
    }

    def parse_date(self, title):
        """Extract (year, month) from a factsheet link title."""
        title_lower = title.lower().strip()
        month = None
        year = None

        for name, num in self.MONTHS.items():
            if name in title_lower:
                month = num
                break

        year_match = re.search(r'(20\d{2})', title)
        if year_match:
            year = int(year_match.group(1))
        else:
            y2_match = re.search(r'[\s,](\d{2})(?:\s|$|\.)', title.strip())
            if y2_match:
                year = 2000 + int(y2_match.group(1))

        if month and year:
            return (year, month)
        return (0, 0)

    def parse(self, response):
        links = response.css('a[href*=".pdf"]')
        factsheets = []

        for link in links:
            href = link.attrib.get("href", "")
            # Concatenate all text nodes (handles text in child spans)
            text = " ".join(link.css("::text").getall()).strip()

            # Match monthly factsheets by URL pattern:
            # URL contains "Factsheet" but NOT performance variants
            is_factsheet = (
                "factsheet" in href.lower()
                and "perf" not in href.lower()
                and "performance" not in href.lower()
            )

            if is_factsheet:
                date_tuple = self.parse_date(text or href)
                factsheets.append({
                    "title": text or href.split("/")[-1],
                    "url": response.urljoin(href),
                    "date": date_tuple,
                })

        if not factsheets:
            self.logger.error("No factsheet links found")
            return

        self.logger.info(f"Found {len(factsheets)} factsheet(s)")

        factsheets.sort(key=lambda x: x["date"], reverse=True)
        latest = factsheets[0]

        self.logger.info(f"Latest: {latest['title']} ({latest['date']})")
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
            r"d:\OCR\OCR\Scraped Factsheets", "helios-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = unquote(response.url.split("/")[-1])
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "helios-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
