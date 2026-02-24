import scrapy
from urllib.parse import urljoin
from scrapy_factsheets.items import FactsheetItem


class AdityaBirlaSpider(scrapy.Spider):
    """
    Spider to download the latest factsheet from Aditya Birla Sun Life Mutual Fund.

    Source page: https://mutualfund.adityabirlacapital.com/forms-and-downloads/factsheets

    The factsheet download section is dynamically loaded via JavaScript,
    but the navigation menu contains a direct link to the latest monthly
    factsheet PDF under "Learnings > Empower - Monthly Factsheet".

    URL pattern: /-/media/bsl/files/resources/factsheets/{year}/abslmf-empower_{month}{yy}.pdf
    """

    name = "aditya_birla"
    start_urls = ["https://mutualfund.adityabirlacapital.com/forms-and-downloads/factsheets"]

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
    }

    def parse(self, response):
        # Look for the "Empower - Monthly Factsheet" link in the navigation
        # It contains a direct PDF link to the latest factsheet
        pdf_links = response.css('a[href*="factsheet"][href$=".pdf"]')

        for link in pdf_links:
            href = link.attrib.get("href", "")
            text = link.css("::text").get("").strip()

            # Look for the factsheet PDF under /media/bsl/files/resources/factsheets/
            if "/media/bsl/files/resources/factsheets/" in href:
                pdf_url = response.urljoin(href)
                self.logger.info(f"Found factsheet: {text} -> {pdf_url}")

                item = FactsheetItem()
                item["fund_name"] = "aditya-birla-sun-life"
                item["file_urls"] = [pdf_url]
                item["factsheet_label"] = text or "ABSL Monthly Factsheet"
                yield item
                return

        # Fallback: look for any PDF link containing "abslmf" or "empower"
        all_links = response.css('a[href$=".pdf"]')
        for link in all_links:
            href = link.attrib.get("href", "")
            text = link.css("::text").get("").strip()

            if "abslmf" in href.lower() or "empower" in href.lower():
                pdf_url = response.urljoin(href)
                self.logger.info(f"Found factsheet (fallback): {text} -> {pdf_url}")

                item = FactsheetItem()
                item["fund_name"] = "aditya-birla-sun-life"
                item["file_urls"] = [pdf_url]
                item["factsheet_label"] = text or "ABSL Monthly Factsheet"
                yield item
                return

        self.logger.warning("No ABSL factsheet PDF found on the page!")
