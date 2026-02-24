"""Wealth Company AMC factsheet spider.

Wealth Company AMC is a Next.js app with a Strapi backend.
Factsheets are available via the API:
  /api/literature-forms
Structure: data.mainTab[2].sections[1].subSections[0].attachments
Each attachment has fileName and file.url (relative to base domain).
Attachments are ordered ascending by date, so last item = latest.
"""
import scrapy
import json
import os
from scrapy_factsheets.items import FactsheetItem


class WealthCompanyAMCSpider(scrapy.Spider):
    name = "wealth_company_amc"
    allowed_domains = ["www.wealthcompanyamc.in", "wealthcompanyamc.in"]

    BASE_URL = "https://www.wealthcompanyamc.in"
    API_URL = f"{BASE_URL}/api/literature-forms"

    def start_requests(self):
        yield scrapy.Request(self.API_URL, callback=self.parse_api)

    def parse_api(self, response):
        try:
            data = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return

        # Navigate: data -> mainTab -> scheme-documents -> factsheets section
        main_tabs = data.get("data", {}).get("mainTab", [])
        factsheet_section = None

        for tab in main_tabs:
            if tab.get("slug") == "scheme-documents":
                for section in tab.get("sections", []):
                    if section.get("slug") == "factsheets":
                        factsheet_section = section
                        break
                break

        if not factsheet_section:
            self.logger.error("Factsheet section not found in API response")
            return

        # Get attachments from the first subSection
        sub_sections = factsheet_section.get("subSections", [])
        if not sub_sections:
            self.logger.error("No subSections found in factsheet section")
            return

        attachments = sub_sections[0].get("attachments", [])
        if not attachments:
            self.logger.error("No attachments found")
            return

        # Latest factsheet is the last item (ascending date order)
        latest = attachments[-1]
        file_info = latest.get("file", {})
        file_url = file_info.get("url", "")
        title = latest.get("fileName", file_info.get("name", "factsheet"))

        if not file_url:
            self.logger.error("No file URL in latest attachment")
            return

        full_url = f"{self.BASE_URL}{file_url}"
        self.logger.info(f"Found: {title} -> {full_url}")

        yield scrapy.Request(
            full_url,
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
            r"d:\OCR\OCR\Scraped Factsheets", "wealth-company-amc"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "wealth-company-amc"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
