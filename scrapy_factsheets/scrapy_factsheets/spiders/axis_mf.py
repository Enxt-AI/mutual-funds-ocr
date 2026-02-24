"""Axis Mutual Fund factsheet spider.

Fetches factsheet data from the CMS API at:
  GET https://www.axismf.com/cms/api/factsheet
which returns a JSON array of all available factsheets.

We pick the latest Direct Plan factsheet (non-Regular, non-Passive)
and download the PDF.
"""
import scrapy
import json
from scrapy_factsheets.items import FactsheetItem


class AxisMFSpider(scrapy.Spider):
    name = "axis_mf"
    allowed_domains = ["www.axismf.com"]

    # CMS API endpoint - returns JSON with all factsheets
    API_URL = "https://www.axismf.com/cms/api/factsheet"

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.axismf.com/downloads?formType=Factsheet",
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            self.API_URL,
            callback=self.parse,
        )

    def parse(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON from CMS API")
            return

        if not data:
            self.logger.warning("No factsheets returned by the API")
            return

        self.logger.info(f"Total factsheets from API: {len(data)}")

        # Filter for the main Direct Plan factsheet
        # Pattern: "Axis Fund Factsheet <Month> <Year>" (not Regular, not Passive)
        direct_factsheets = []
        for entry in data:
            name = entry.get("field_pdf_name", "")
            # Direct plan factsheet: contains "Axis Fund Factsheet"
            # but NOT "Regular" and NOT "Passive"
            if "Axis Fund Factsheet" in name \
               and "Regular" not in name \
               and "Passive" not in name:
                direct_factsheets.append(entry)

        if not direct_factsheets:
            self.logger.warning("No Direct Plan factsheets found, trying all")
            # Fallback: pick the first entry that looks like a factsheet
            for entry in data:
                name = entry.get("field_pdf_name", "")
                if "Factsheet" in name and "Regular" not in name:
                    direct_factsheets.append(entry)

        if not direct_factsheets:
            self.logger.error("No suitable factsheets found at all")
            return

        # The API returns data sorted by date (latest first)
        latest = direct_factsheets[0]

        name = latest["field_pdf_name"]
        month = latest.get("field_pdf_month", "")
        year = latest.get("field_pdf_year", "")
        relative_url = latest["field_pdf_file_url"]

        # Build absolute URL
        pdf_url = response.urljoin(relative_url)

        self.logger.info(f"Latest factsheet: {name} ({month} {year})")
        self.logger.info(f"PDF URL: {pdf_url}")

        item = FactsheetItem()
        item["fund_name"] = "axis-mf"
        item["file_urls"] = [pdf_url]
        item["factsheet_label"] = f"{name}"
        yield item
