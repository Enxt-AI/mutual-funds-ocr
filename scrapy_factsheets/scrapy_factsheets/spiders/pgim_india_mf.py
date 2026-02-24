"""PGIM India Mutual Fund factsheet spider.

PGIM India is an Angular SPA. The factsheet data comes from:
  GET /api/v1/brochure/published/form -> JSON with all form entries + pdfPath
The factsheet PDF is served via:
  /api/v1/brochure/about-us/image/{Factsheet - Month Year}.pdf
"""
import scrapy
import json
import os
import re
from urllib.parse import quote
from scrapy_factsheets.items import FactsheetItem


class PGIMIndiaMFSpider(scrapy.Spider):
    name = "pgim_india_mf"
    allowed_domains = ["www.pgimindia.com"]
    
    FORMS_API = "https://www.pgimindia.com/api/v1/brochure/published/form"

    def start_requests(self):
        yield scrapy.Request(
            self.FORMS_API,
            callback=self.parse_forms,
            headers={"Accept": "application/json"},
        )

    def parse_forms(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse forms API response")
            return

        result = data.get("data", {})
        
        # Search all tabs for factsheet entries
        factsheet_entry = None
        for tab_key, forms in result.items():
            if not isinstance(forms, list):
                continue
            for form in forms:
                title = form.get("title", "") or form.get("formName", "")
                if "factsheet" in title.lower():
                    self.logger.info(f"Found factsheet: {title} in tab {tab_key}")
                    factsheet_entry = form
                    break
            if factsheet_entry:
                break

        if factsheet_entry:
            pdf_path = factsheet_entry.get("pdfPath", "")
            title = factsheet_entry.get("title", "") or factsheet_entry.get("formName", "")
            
            if pdf_path:
                pdf_url = response.urljoin(pdf_path)
                self.logger.info(f"Downloading from pdfPath: {pdf_url}")
                yield scrapy.Request(
                    pdf_url,
                    callback=self.save_pdf,
                    meta={"title": title},
                    dont_filter=True,
                )
                return
            else:
                # Use the known URL pattern
                encoded_title = quote(title)
                pdf_url = f"https://www.pgimindia.com/api/v1/brochure/about-us/image/{encoded_title}.pdf"
                self.logger.info(f"Downloading from URL pattern: {pdf_url}")
                yield scrapy.Request(
                    pdf_url,
                    callback=self.save_pdf,
                    meta={"title": title},
                    dont_filter=True,
                )
                return

        # Fallback: try the known URL pattern directly
        self.logger.warning("No factsheet in API, trying direct URL pattern")
        from datetime import datetime
        now = datetime.now()
        month = now.strftime("%B")
        year = now.strftime("%Y")
        title = f"Factsheet - {month} {year}"
        encoded = quote(title)
        pdf_url = f"https://www.pgimindia.com/api/v1/brochure/about-us/image/{encoded}.pdf"
        self.logger.info(f"Trying: {pdf_url}")
        yield scrapy.Request(
            pdf_url,
            callback=self.save_pdf,
            meta={"title": title, "fallback_month": 1},
            dont_filter=True,
        )

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200 or len(response.body) < 1000:
            # Try previous month
            fallback = response.meta.get("fallback_month", 0)
            if fallback and fallback <= 3:
                from datetime import datetime, timedelta
                now = datetime.now()
                dt = now - timedelta(days=30 * fallback)
                month = dt.strftime("%B")
                year = dt.strftime("%Y")
                title = f"Factsheet - {month} {year}"
                encoded = quote(title)
                pdf_url = f"https://www.pgimindia.com/api/v1/brochure/about-us/image/{encoded}.pdf"
                self.logger.info(f"Trying older month: {pdf_url}")
                yield scrapy.Request(
                    pdf_url,
                    callback=self.save_pdf,
                    meta={"title": title, "fallback_month": fallback + 1},
                    dont_filter=True,
                )
            else:
                self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "pgim-india-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "pgim-india-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
