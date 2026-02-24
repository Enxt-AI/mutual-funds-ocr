"""DSP Mutual Fund factsheet spider.

DSP MF uses a JSON API at /downloads.json with category/sub_category filters.
The first item in the response is the latest factsheet.
PDF URLs redirect (307) so we follow the redirect to get the final URL.
"""
import scrapy
import json
import os
from scrapy_factsheets.items import FactsheetItem


class DSPMFSpider(scrapy.Spider):
    name = "dsp_mf"
    allowed_domains = ["www.dspim.com"]

    def start_requests(self):
        url = (
            "https://www.dspim.com/downloads.json"
            "?page=1&per_page=5"
            "&category=Information+Documents"
            "&sub_category=Factsheets"
        )
        yield scrapy.Request(url, headers={"Accept": "application/json"})

    def parse(self, response):
        data = json.loads(response.text)

        items = data.get("data", [])
        if not items:
            self.logger.error("No factsheet items in API response")
            return

        self.logger.info(f"Found {len(items)} factsheet(s)")

        # First item is the latest
        latest = items[0]
        title = latest.get("title", "")
        pdf_url = latest.get("pdf_url", "")

        if not pdf_url:
            self.logger.error("No PDF URL in latest item")
            return

        self.logger.info(f"Latest: {title}")
        self.logger.info(f"PDF URL: {pdf_url}")

        # Follow redirects manually to get the actual PDF
        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={
                "title": title,
                "handle_httpstatus_list": [307, 301, 302],
            },
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        # If we got a redirect, follow it
        if response.status in (301, 302, 307):
            redirect_url = response.headers.get("Location", b"").decode("utf-8")
            if redirect_url:
                self.logger.info(f"Following redirect to: {redirect_url}")
                yield scrapy.Request(
                    response.urljoin(redirect_url),
                    callback=self.save_pdf,
                    meta={"title": title, "handle_httpstatus_list": [307, 301, 302]},
                    dont_filter=True,
                )
                return

        # We have the actual PDF content
        if response.status == 200:
            save_dir = os.path.join(
                r"d:\OCR\OCR\Scraped Factsheets", "dsp-mutual-fund"
            )
            os.makedirs(save_dir, exist_ok=True)

            filename = response.url.split("/")[-1]
            filepath = os.path.join(save_dir, filename)

            with open(filepath, "wb") as f:
                f.write(response.body)

            self.logger.info(f"Saved: {filepath}")

            item = FactsheetItem()
            item["fund_name"] = "dsp-mutual-fund"
            item["file_urls"] = []  # Already saved manually
            item["files"] = [{"path": filepath, "url": response.url}]
            item["factsheet_label"] = title
            yield item
        else:
            self.logger.error(
                f"Failed to download PDF: status {response.status}"
            )
