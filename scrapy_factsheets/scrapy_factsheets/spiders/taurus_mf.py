"""Taurus Mutual Fund factsheet spider.

Taurus MF uses Drupal Views with exposed filter.
Views AJAX POST to /views/ajax with field_factsheet_item_target_id=<year_tid>
Returns HTML with PDF link(s) under /sites/default/files/downloads/.
Year 2026 = tid 565, 2025 = tid 556, etc.
"""
import json
import scrapy
import os
import re
from urllib.parse import unquote
from scrapy_factsheets.items import FactsheetItem


class TaurusMFSpider(scrapy.Spider):
    name = "taurus_mf"
    allowed_domains = ["www.taurusmutualfund.com", "taurusmutualfund.com"]

    VIEWS_AJAX_URL = "https://www.taurusmutualfund.com/views/ajax"

    # Year TID mapping (latest first)
    YEAR_TIDS = [
        ("2026", "565"),
        ("2025", "556"),
        ("2024", "516"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.found = False

    def start_requests(self):
        yield self._make_request(0)

    def _make_request(self, idx):
        year, tid = self.YEAR_TIDS[idx]
        return scrapy.FormRequest(
            self.VIEWS_AJAX_URL,
            formdata={
                "view_name": "factsheet",
                "view_display_id": "page_1",
                "view_args": "",
                "view_path": "/factsheet",
                "view_dom_id": "d5f1e851a8167d48810530ac5ad4dde4d1ac38259574f15c0a76e45b3485a3b5",
                "pager_element": "0",
                "field_factsheet_item_target_id": tid,
                "_drupal_ajax": "1",
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
            callback=self.parse_ajax,
            meta={"year": year, "idx": idx},
            dont_filter=True,
        )

    def parse_ajax(self, response):
        if self.found:
            return

        year = response.meta["year"]
        idx = response.meta["idx"]

        try:
            text = response.text
            # Drupal wraps AJAX response in <textarea> tags
            text = re.sub(r'^<textarea>', '', text)
            text = re.sub(r'</textarea>$', '', text)
            result = json.loads(text)
        except Exception as e:
            self.logger.error(f"JSON parse error for {year}: {e}")
            self.logger.error(f"Response preview: {response.text[:200]}")
            return

        # Find PDF links in the returned HTML
        pdf_url = None
        for item in result:
            if item.get("command") == "insert" and "data" in item:
                pdfs = re.findall(r'href="([^"]*\.pdf[^"]*)"', item["data"])
                if pdfs:
                    pdf_url = pdfs[0].strip()
                    break

        if not pdf_url:
            self.logger.info(f"No factsheet PDF for {year}, trying previous year...")
            if idx + 1 < len(self.YEAR_TIDS):
                yield self._make_request(idx + 1)
            return

        self.found = True

        # Make absolute URL
        if pdf_url.startswith("/"):
            pdf_url = f"https://www.taurusmutualfund.com{pdf_url}"

        filename = unquote(pdf_url.split("/")[-1]).replace(".pdf", "")
        title = f"Taurus MF {filename}"
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
            r"d:\OCR\OCR\Scraped Factsheets", "taurus-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "taurus-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
