"""ICICI Prudential Mutual Fund factsheet spider.

ICICI Pru AMC stores factsheets as Azure blobs at a predictable URL:
  https://www.icicipruamc.com/blob/downloads/Files/
    Historic%20Factsheets/{FY_START}-{FY_END}/
    Complete%20Factsheet%20{Month}%20{Year}.pdf

The financial year runs April→March. For example, January 2026 falls
in FY 2025-2026.  The spider constructs URLs for recent months and
downloads the first one that responds with 200.
"""
import scrapy
import os
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
from scrapy_factsheets.items import FactsheetItem


class IciciPruMFSpider(scrapy.Spider):
    name = "icici_pru_mf"
    allowed_domains = ["www.icicipruamc.com", "icicipruamc.com"]

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    BASE_URL = (
        "https://www.icicipruamc.com/blob/downloads/Files/"
        "Historic%20Factsheets"
    )

    def _financial_year(self, year, month):
        """Return 'YYYY-YYYY' financial year string (Apr-Mar cycle)."""
        if month >= 4:  # Apr-Dec → FY is year to year+1
            return f"{year}-{year + 1}"
        else:  # Jan-Mar → FY is year-1 to year
            return f"{year - 1}-{year}"

    def _build_url(self, year, month):
        """Build the blob URL for a given month/year."""
        fy = self._financial_year(year, month)
        month_name = self.MONTHS[month - 1]
        filename = f"Complete%20Factsheet%20{month_name}%20{year}.pdf"
        return f"{self.BASE_URL}/{fy}/{filename}"

    def start_requests(self):
        """Try most recent month first, chain to older months on failure."""
        yield self._request_for_offset(0)

    def _request_for_offset(self, offset):
        """Build a request for the month at the given offset from now."""
        now = datetime.now()
        dt = now - timedelta(days=30 * offset)
        year, month = dt.year, dt.month
        url = self._build_url(year, month)
        month_name = self.MONTHS[month - 1]
        self.logger.info(
            f"Trying: {month_name} {year} → {unquote(url.split('/')[-1])}"
        )
        return scrapy.Request(
            url,
            callback=self.check_and_save,
            errback=self.handle_error,
            meta={
                "month_name": month_name,
                "year": year,
                "month_offset": offset,
            },
            dont_filter=True,
        )

    def _try_next_month(self, current_offset):
        """Try the next older month if we haven't exhausted attempts."""
        next_offset = current_offset + 1
        if next_offset < 4:
            return self._request_for_offset(next_offset)
        self.logger.error("No factsheet found in the last 4 months")
        return None

    def handle_error(self, failure):
        meta = failure.request.meta
        self.logger.warning(
            f"Failed: {meta['month_name']} {meta['year']}: {failure.value}"
        )
        req = self._try_next_month(meta["month_offset"])
        if req:
            yield req

    def check_and_save(self, response):
        month_name = response.meta["month_name"]
        year = response.meta["year"]
        offset = response.meta["month_offset"]

        # Skip non-PDF responses (404s return XML/HTML)
        ct = response.headers.get("Content-Type", b"").decode("utf-8", errors="ignore")
        if response.status != 200 or "pdf" not in ct.lower():
            self.logger.info(
                f"Not available: {month_name} {year} "
                f"(status={response.status}, ct={ct[:40]})"
            )
            req = self._try_next_month(offset)
            if req:
                yield req
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "icici-prudential-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = unquote(response.url.split("/")[-1])
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        title = f"Complete Factsheet {month_name} {year}"
        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "icici-prudential-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
