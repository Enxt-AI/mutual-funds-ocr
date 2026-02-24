"""UNIFI Mutual Fund factsheet spider.

UNIFI MF is a WordPress site with factsheet PDFs directly linked
in the HTML table at /factsheet/.
PDFs are at /wp-content/uploads/fund-sheets/Unifi-MF-Factsheet-*.pdf
Note: Site has SSL certificate issues, so we disable verification.
"""
import scrapy
import os
from scrapy_factsheets.items import FactsheetItem


class UnifiMFSpider(scrapy.Spider):
    name = "unifi_mf"
    allowed_domains = ["unifimf.com"]
    start_urls = ["https://unifimf.com/factsheet/"]

    custom_settings = {
        "DOWNLOADER_CLIENT_TLS_METHOD": "TLSv1.2",
    }

    def parse(self, response):
        # Find the first PDF link containing 'fund-sheets' in the path
        pdf_links = response.css(
            'a[href*="fund-sheets"][href$=".pdf"]::attr(href)'
        ).getall()

        if not pdf_links:
            # Fallback: any PDF with factsheet in name
            pdf_links = response.css(
                'a[href*="Factsheet"][href$=".pdf"]::attr(href)'
            ).getall()

        if not pdf_links:
            self.logger.error("No factsheet PDF links found")
            return

        pdf_url = response.urljoin(pdf_links[0])
        filename = pdf_url.split("/")[-1].replace(".pdf", "")
        title = f"UNIFI MF {filename}"
        self.logger.info(f"Found: {title} -> {pdf_url}")

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
            r"d:\OCR\OCR\Scraped Factsheets", "unifi-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "unifi-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
