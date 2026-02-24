import re
import scrapy
from scrapy_factsheets.items import FactsheetItem


# Month ordering for date comparison
MONTH_ORDER = {
    "jan": 1, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "aug": 8, "sept": 9, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


class AngelOneSpider(scrapy.Spider):
    """
    Spider to download the latest factsheet from Angel One Mutual Fund.

    Source page: https://www.angelonemf.com/downloads

    The factsheet PDFs are NOT in <a> tags — they're embedded in a JavaScript
    `factsheetsData` JSON object inside a <script> tag. This spider uses regex
    to extract all factsheet URLs from the raw HTML, filters for the
    consolidated "Schemes" factsheet, and picks the latest by date.

    URL pattern:
      https://cms.angelonemf.com/amc-cms/wp-content/uploads/formidable/15/
      Factsheet-Angel-One-Mutual-Fund-Schemes-{Month}-{Year}[-suffix].pdf
    """

    name = "angel_one"
    start_urls = ["https://www.angelonemf.com/downloads"]
    allowed_domains = ["www.angelonemf.com", "cms.angelonemf.com"]

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    }

    def parse(self, response):
        # Extract all factsheet URLs from raw HTML (they're in JS, not <a> tags)
        all_urls = re.findall(
            r'https://cms\.angelonemf\.com/amc-cms/wp-content/uploads/formidable/\d+/Factsheet[^\s"\'\\]+\.pdf',
            response.text,
            re.IGNORECASE,
        )
        self.logger.info(f"Found {len(all_urls)} factsheet URLs in page source")

        # Filter for consolidated "Schemes" factsheets (not individual fund ones)
        schemes_urls = [
            u for u in all_urls if "Mutual-Fund-Schemes" in u
        ]
        self.logger.info(f"Consolidated Schemes factsheets: {len(schemes_urls)}")

        if not schemes_urls:
            self.logger.warning("No consolidated factsheet found, trying all factsheet URLs")
            schemes_urls = all_urls

        # Pick the latest by parsing month/year from the filename
        best_url = None
        best_date = (0, 0)  # (year, month_num)

        for url in schemes_urls:
            # Extract month and year: e.g. "...-Jan-2026.pdf" or "...-Jan-2026-1.pdf"
            match = re.search(
                r'-([A-Za-z]+)-(\d{4})(?:-\d+)*\.pdf$', url
            )
            if match:
                month_str = match.group(1).lower()
                year = int(match.group(2))
                month_num = MONTH_ORDER.get(month_str, 0)
                if (year, month_num) > best_date:
                    best_date = (year, month_num)
                    best_url = url

        if best_url:
            self.logger.info(f"Latest factsheet: {best_url}")
            item = FactsheetItem()
            item["fund_name"] = "angel-one"
            item["file_urls"] = [best_url]
            item["factsheet_label"] = f"Angel One Factsheet {best_date[0]}"
            yield item
        else:
            self.logger.warning("Could not determine latest Angel One factsheet!")
