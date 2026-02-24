"""Jio BlackRock Mutual Fund factsheet spider.

Jio BlackRock AMC is a Next.js app that uses React Server Actions.
The factsheet data is fetched by POSTing to the factsheet page URL
with a Next-Action header containing the server action ID.

Request:
  POST https://www.jioblackrockamc.com/statutory-disclosure/fund-documents/factsheet
  Headers:
    Next-Action: 60c09b509b7c9285121790d68606ebca78d1b505c6
    Accept: text/x-component
    Content-Type: text/plain;charset=UTF-8
  Body: ["factsheet",{"year":"$undefined","month":"<Month>","date":"$undefined"}]

Response (RSC wire format):
  1:{"data":[{"id":...,"title":"...","file":{"url":"https://...pdf","ext":".pdf"}}],...}
"""
import scrapy
import json
import os
import re
from datetime import datetime, timedelta
from scrapy_factsheets.items import FactsheetItem


class JioBlackRockMFSpider(scrapy.Spider):
    name = "jio_blackrock_mf"
    allowed_domains = [
        "www.jioblackrockamc.com",
        "jioblackrockamc.com",
        "cdnstorage-ddh3hqhvg3gyedd9.a02.azurefd.net",
    ]

    PAGE_URL = "https://www.jioblackrockamc.com/statutory-disclosure/fund-documents/factsheet"
    ACTION_ID = "60c09b509b7c9285121790d68606ebca78d1b505c6"

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/x-component",
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": "https://www.jioblackrockamc.com",
            "Referer": "https://www.jioblackrockamc.com/statutory-disclosure/fund-documents/factsheet",
            "Next-Action": ACTION_ID,
        },
    }

    def start_requests(self):
        """Try current month first, chain to older months on 'no data'."""
        yield self._request_for_offset(0)

    def _request_for_offset(self, offset):
        now = datetime.now()
        dt = now - timedelta(days=30 * offset)
        month_name = self.MONTHS[dt.month - 1]

        body = json.dumps([
            "factsheet",
            {"year": "$undefined", "month": month_name, "date": "$undefined"},
        ])

        self.logger.info(f"Trying month: {month_name}")
        return scrapy.Request(
            self.PAGE_URL,
            method="POST",
            body=body,
            callback=self.parse_rsc,
            errback=self.handle_error,
            meta={"offset": offset, "month": month_name},
            dont_filter=True,
        )

    def handle_error(self, failure):
        offset = failure.request.meta.get("offset", 0)
        month = failure.request.meta.get("month", "")
        self.logger.warning(f"Request failed for {month}: {failure.value}")
        if offset < 3:
            yield self._request_for_offset(offset + 1)

    def parse_rsc(self, response):
        offset = response.meta["offset"]
        month = response.meta["month"]

        # Parse RSC wire format — JSON data is on the line starting with "1:"
        data_items = []
        for line in response.text.split("\n"):
            if line.startswith("1:"):
                try:
                    payload = json.loads(line[2:])
                    data_items = payload.get("data", [])
                except json.JSONDecodeError:
                    pass

        if not data_items:
            self.logger.info(f"No factsheets for {month}")
            if offset < 3:
                yield self._request_for_offset(offset + 1)
            return

        # Take the first (latest) factsheet
        item = data_items[0]
        title = item.get("title", "")
        file_info = item.get("file", {})
        pdf_url = file_info.get("url", "")

        if not pdf_url:
            self.logger.error(f"No PDF URL found for: {title}")
            return

        self.logger.info(f"Found: {title}")
        self.logger.info(f"PDF URL: {pdf_url}")

        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={"title": title, "uid": item.get("uid", "")},
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]
        uid = response.meta.get("uid", "")

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "jio-blackrock-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{uid or title}.pdf".replace(" ", "-").replace("/", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "jio-blackrock-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
