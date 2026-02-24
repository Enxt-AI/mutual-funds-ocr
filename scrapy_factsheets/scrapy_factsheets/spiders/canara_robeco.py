"""Canara Robeco Mutual Fund factsheet spider.

The site is a WordPress site with direct PDF links in the HTML.
Factsheets follow the pattern:
/wp-content/uploads/{year}/{month}/Canara-Robeco-factsheet-as-on-{Month}-{Year}.pdf
"""
import scrapy
import re
from scrapy_factsheets.items import FactsheetItem


class CanaraRobecoSpider(scrapy.Spider):
    name = "canara_robeco"
    allowed_domains = ["www.canararobeco.com"]
    start_urls = [
        "https://www.canararobeco.com/documents/forms-downloads/"
        "forms-information-documents/information-documents/factsheets/"
    ]

    def parse(self, response):
        # Find all PDF links that contain 'factsheet' in the URL
        all_links = response.css('a[href$=".pdf"]::attr(href)').getall()

        factsheet_links = []
        for link in all_links:
            if "factsheet" in link.lower():
                full_url = response.urljoin(link)
                if full_url not in factsheet_links:
                    factsheet_links.append(full_url)

        self.logger.info(f"Found {len(factsheet_links)} factsheet PDF(s)")
        for link in factsheet_links[:5]:
            self.logger.info(f"  {link}")

        if not factsheet_links:
            self.logger.error("No factsheet PDF links found")
            return

        # Sort by upload date in URL: /uploads/{year}/{month}/
        # e.g., /uploads/2026/02/ comes after /uploads/2026/01/
        def sort_key(url):
            match = re.search(r'/uploads/(\d{4})/(\d{2})/', url)
            if match:
                return (int(match.group(1)), int(match.group(2)))
            return (0, 0)

        factsheet_links.sort(key=sort_key, reverse=True)
        latest_url = factsheet_links[0]

        self.logger.info(f"Latest factsheet: {latest_url}")

        # Extract label from filename
        filename = latest_url.split("/")[-1]
        label = re.sub(r'-?\d*\.pdf$', '', filename)
        label = label.replace('-', ' ')

        self.logger.info(f"Label: {label}")

        item = FactsheetItem()
        item["fund_name"] = "canara-robeco"
        item["file_urls"] = [latest_url]
        item["factsheet_label"] = label
        yield item
