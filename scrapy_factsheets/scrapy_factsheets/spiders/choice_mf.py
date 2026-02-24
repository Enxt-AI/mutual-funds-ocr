"""Choice Mutual Fund factsheet spider.

Choice MF is a Next.js app. Factsheet data is hardcoded in a JS chunk
(3804.*.js) as a documents array with title/filePath pairs.
The spider fetches the HTML page to find the chunk URL, then parses the
chunk to extract the latest factsheet PDF path.
"""
import scrapy
import re
import json
from scrapy_factsheets.items import FactsheetItem


class ChoiceMFSpider(scrapy.Spider):
    name = "choice_mf"
    allowed_domains = ["choicemf.com", "static.choicemf.com"]
    start_urls = ["https://choicemf.com/disclosures/factsheets"]

    def parse(self, response):
        # Find the 3804.*.js chunk URL from preload links or script tags
        chunk_url = None

        # Check preload links first
        preloads = response.css('link[rel="preload"][href*="3804"]::attr(href)').getall()
        if preloads:
            chunk_url = response.urljoin(preloads[0])
        else:
            # Fallback: search in script tags
            scripts = response.css('script[src*="3804"]::attr(src)').getall()
            if scripts:
                chunk_url = response.urljoin(scripts[0])

        if not chunk_url:
            self.logger.error("Could not find factsheet chunk (3804.*.js)")
            return

        self.logger.info(f"Factsheet chunk: {chunk_url}")
        yield scrapy.Request(chunk_url, callback=self.parse_chunk)

    def parse_chunk(self, response):
        text = response.text

        # Extract the documents array from the JS
        # Pattern: {title:"January 2026",filePath:"/factsheet/...pdf"}
        docs = re.findall(
            r'\{title:"([^"]+)",filePath:"([^"]+)"\}',
            text
        )

        if not docs:
            self.logger.error("No factsheet documents found in chunk")
            return

        self.logger.info(f"Found {len(docs)} factsheet(s):")
        for title, path in docs:
            self.logger.info(f"  {title}: {path}")

        # The last document in the array is the latest
        latest_title, latest_path = docs[-1]

        # Build PDF URL on the main domain
        pdf_url = f"https://choicemf.com{latest_path}"
        self.logger.info(f"Selected: {latest_title}")
        self.logger.info(f"PDF URL: {pdf_url}")

        item = FactsheetItem()
        item["fund_name"] = "choice-mf"
        item["file_urls"] = [pdf_url]
        item["factsheet_label"] = latest_title
        yield item
