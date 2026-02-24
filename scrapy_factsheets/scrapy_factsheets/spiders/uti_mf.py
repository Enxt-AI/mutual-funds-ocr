"""UTI Mutual Fund factsheet spider.

UTI MF is an Angular SPA with a CMS API.
The factsheet API is at:
  /api/get-fact-sheet?year={year}&month={month}
Month names are full English names (e.g. "January").
Available year/month combos come from:
  /api/page/forms-and-downloads-downloads -> field_component[12].filters[0].filter_year_month
Returns JSON with rows containing PDF download URLs on CloudFront CDN.
"""
import scrapy
import json
import os
from datetime import datetime
from scrapy_factsheets.items import FactsheetItem


class UTIMFSpider(scrapy.Spider):
    name = "uti_mf"
    allowed_domains = ["www.utimf.com", "utimf.com", "d3ce1o48hc5oli.cloudfront.net"]

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    def start_requests(self):
        # Start with current month, fall back to previous months
        now = datetime.now()
        url = self._build_url(now.year, now.month)
        yield scrapy.Request(
            url,
            callback=self.parse_api,
            meta={"year": now.year, "month_idx": now.month},
            dont_filter=True,
        )

    def _build_url(self, year, month_idx):
        month_name = self.MONTHS[month_idx - 1]
        return f"https://www.utimf.com/api/get-fact-sheet?year={year}&month={month_name}"

    def parse_api(self, response):
        year = response.meta["year"]
        month_idx = response.meta["month_idx"]
        month_name = self.MONTHS[month_idx - 1]

        try:
            data = json.loads(response.text)
        except Exception as e:
            self.logger.error(f"JSON parse error: {e}")
            return

        rows = data.get("rows", [])

        # Filter for Active factsheet only (exclude Passive)
        active_row = None
        for row in rows:
            name = row.get("name", "")
            if "passive" in name.lower():
                continue
            pdf_url = row.get("url") or row.get("doc", "")
            if pdf_url and ".pdf" in pdf_url.lower():
                active_row = row
                break

        if not active_row:
            self.logger.info(f"No Active factsheet for {month_name} {year}, trying previous month")
            # Try previous month
            m = month_idx - 1
            y = year
            if m <= 0:
                m = 12
                y -= 1
            if y >= year - 1:  # Don't go back more than a year
                url = self._build_url(y, m)
                yield scrapy.Request(
                    url,
                    callback=self.parse_api,
                    meta={"year": y, "month_idx": m},
                    dont_filter=True,
                )
            return

        pdf_url = active_row.get("url") or active_row.get("doc", "")
        name = active_row.get("name", "")
        clean_name = name if name else pdf_url.split("/")[-1].split("?")[0]
        self.logger.info(f"Found: {clean_name} -> {pdf_url}")

        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={"title": clean_name},
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "uti-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-").replace("?", "")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "uti-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
