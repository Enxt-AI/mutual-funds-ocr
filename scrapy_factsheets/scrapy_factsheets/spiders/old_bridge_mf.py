"""Old Bridge Mutual Fund factsheet spider.

Old Bridge MF factsheet page has direct PDF links in server-rendered HTML.
The latest factsheet appears first under the "Factsheet" heading.
PDFs at /uploads/ path with hash suffixes.
"""
import scrapy
import os
from scrapy_factsheets.items import FactsheetItem


class OldBridgeMFSpider(scrapy.Spider):
    name = "old_bridge_mf"
    allowed_domains = ["www.oldbridgemf.com", "oldbridgemf.com"]
    start_urls = ["https://www.oldbridgemf.com/factsheet.html"]

    def parse(self, response):
        # Find first PDF link under factsheet section
        pdf_links = response.css('a[href$=".pdf"]::attr(href)').getall()
        factsheet_pdfs = [l for l in pdf_links if "factsheet" in l.lower() or "Factsheet" in l]

        self.logger.info(f"Found {len(factsheet_pdfs)} factsheet PDF(s)")

        if not factsheet_pdfs:
            self.logger.error("No factsheet PDF links found!")
            return

        # Get preceding h6 text as label
        # The structure is: h6 (month) then a[href=pdf]
        first_h6 = response.css("h6::text").get("").strip()
        pdf_url = response.urljoin(factsheet_pdfs[0])

        title = f"Old Bridge MF Factsheet - {first_h6}" if first_h6 else "Old Bridge MF Factsheet"
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
            r"d:\OCR\OCR\Scraped Factsheets", "old-bridge-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "old-bridge-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
