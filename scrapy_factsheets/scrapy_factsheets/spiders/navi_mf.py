"""Navi Mutual Fund factsheet spider.

Navi MF uses a WordPress REST API:
  1. GET the downloads page to extract the WP nonce
  2. POST /wp-json/nv/v1/documents with WP-NONCE header
     Body: {category: "867", type: "Monthly", value: <month>, 
            financial_year: <year>, order: "DESC"}
  Response: {success: true, data: [{title, url}]}
PDFs hosted on public-assets.prod.navi-tech.in.
"""
import scrapy
import json
import os
import re
from datetime import datetime
from scrapy_factsheets.items import FactsheetItem


class NaviMFSpider(scrapy.Spider):
    name = "navi_mf"
    allowed_domains = [
        "navi.com",
        "public-assets.prod.navi-tech.in",
    ]

    PAGE_URL = "https://navi.com/mutual-fund/downloads/factsheet"
    API_URL = "https://navi.com/wp-json/nv/v1/documents"

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    def start_requests(self):
        """First fetch the page to extract the WP nonce."""
        yield scrapy.Request(self.PAGE_URL, callback=self.parse_nonce)

    def parse_nonce(self, response):
        """Extract nonce then call the REST API."""
        nonce_match = re.search(r'"nonce"\s*:\s*"([^"]+)"', response.text)
        if not nonce_match:
            self.logger.error("Could not extract WP nonce!")
            return

        nonce = nonce_match.group(1)
        self.logger.info(f"Extracted nonce: {nonce}")

        # Determine current month & financial year
        now = datetime.now()
        month = now.month - 1 or 12  # previous month's factsheet
        year = now.year if month != 12 else now.year - 1
        fy = f"{year}-{year + 1}" if month >= 4 else f"{year - 1}-{year}"

        yield scrapy.Request(
            self.API_URL,
            method="POST",
            body=f"category=867&type=Monthly&value={self.MONTHS[month - 1]}&financial_year={fy}&order=DESC",
            headers={
                "WP-NONCE": nonce,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            callback=self.parse_api,
            meta={"nonce": nonce, "month_offset": 0},
            dont_filter=True,
        )

    def parse_api(self, response):
        data = json.loads(response.text)

        if not data.get("success") or not data.get("data"):
            offset = response.meta.get("month_offset", 0) + 1
            if offset < 3:
                self.logger.info(f"No data, trying offset {offset}")
                now = datetime.now()
                month = now.month - 1 - offset
                if month <= 0:
                    month += 12
                year = now.year if month >= now.month else now.year - (1 if month > now.month - 1 - offset else 0)
                # Recalculate properly
                from dateutil.relativedelta import relativedelta
                dt = now - relativedelta(months=1 + offset)
                month = dt.month
                year = dt.year
                fy = f"{year}-{year + 1}" if month >= 4 else f"{year - 1}-{year}"

                yield scrapy.Request(
                    self.API_URL,
                    method="POST",
                    body=f"category=867&type=Monthly&value={self.MONTHS[month - 1]}&financial_year={fy}&order=DESC",
                    headers={
                        "WP-NONCE": response.meta["nonce"],
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    callback=self.parse_api,
                    meta={"nonce": response.meta["nonce"], "month_offset": offset},
                    dont_filter=True,
                )
            return

        items = data["data"]
        self.logger.info(f"Found {len(items)} factsheet(s)")

        for item in items:
            title = item.get("title", "").replace("&#8211;", "-")
            pdf_url = item.get("url", "").replace("\\/", "/")

            if not pdf_url:
                continue

            self.logger.info(f"Downloading: {title} -> {pdf_url}")

            yield scrapy.Request(
                pdf_url,
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
            r"d:\OCR\OCR\Scraped Factsheets", "navi-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        fi = FactsheetItem()
        fi["fund_name"] = "navi-mutual-fund"
        fi["file_urls"] = []
        fi["files"] = [{"path": filepath, "url": response.url}]
        fi["factsheet_label"] = title
        yield fi
