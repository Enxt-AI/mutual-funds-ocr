"""HSBC Mutual Fund factsheet spider.

HSBC Asset Management India hosts investor resources at:
  https://www.assetmanagement.hsbc.co.in/en/mutual-funds/investor-resources
The page lists all document types; we filter for "Fund factsheets" category.
Factsheet links use class `document-list__link` inside
`div.document-list__item-heading`, with a sibling `<span>` containing
"(Fund factsheets X.XXMB)".

Title pattern: "The Asset as on - [Month] [Year]"
              or "The Asset, Factsheet - [Month] [Year]"
"""
import scrapy
import re
import os
from urllib.parse import unquote
from scrapy_factsheets.items import FactsheetItem


class HsbcMFSpider(scrapy.Spider):
    name = "hsbc_mf"
    allowed_domains = ["www.assetmanagement.hsbc.co.in", "assetmanagement.hsbc.co.in"]
    start_urls = [
        "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/investor-resources"
        "?Date=&Cap=&Doc=fund-factsheets"
    ]

    MONTHS = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
        "oct": 10, "nov": 11, "dec": 12,
    }

    def parse_date(self, title):
        """Extract (year, month) from factsheet title like
        'The Asset as on - January 2026'."""
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

        if month and year:
            return (year, month)
        return (0, 0)

    def parse(self, response):
        # Each factsheet entry is a div.document-list__item-heading containing:
        #   <a class="document-list__link" href="...pdf">Title</a>
        #   <span>(Fund factsheets X.XXMB)</span>
        headings = response.css("div.document-list__item-heading")
        factsheets = []

        for heading in headings:
            # Check if this is a "Fund factsheets" entry
            desc = heading.css("span::text").get("")
            if "fund factsheets" not in desc.lower():
                continue

            link = heading.css("a.document-list__link")
            if not link:
                continue

            href = link.attrib.get("href", "")
            text = " ".join(link.css("::text").getall()).strip()

            if not href:
                continue

            date_tuple = self.parse_date(text)
            factsheets.append({
                "title": text,
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
            r"d:\OCR\OCR\Scraped Factsheets", "hsbc-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = unquote(response.url.split("/")[-1])
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "hsbc-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
