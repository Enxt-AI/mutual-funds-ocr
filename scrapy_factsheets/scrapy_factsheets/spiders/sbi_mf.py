"""SBI Mutual Fund factsheet spider.

SBI MF factsheet page uses AJAX. The API endpoint:
  POST /ajaxcall/CMS/GetRecentFactSheets -> HTML table with PDF links
Returns links like:
  /docs/default-source/scheme-factsheets/all-sbimf-schemes-factsheet-january-2026.pdf
We pick the "All SBIMF Schemes" combined factsheet (the most comprehensive one).
"""
import scrapy
import os
import re
from scrapy_factsheets.items import FactsheetItem


class SBIMFSpider(scrapy.Spider):
    name = "sbi_mf"
    allowed_domains = ["www.sbimf.com"]

    RECENT_API = "https://www.sbimf.com/ajaxcall/CMS/GetRecentFactSheets"

    def start_requests(self):
        yield scrapy.Request(
            self.RECENT_API,
            method="POST",
            headers={
                "Content-Type": "application/json;charset=utf-8",
                "Referer": "https://www.sbimf.com/factsheets",
            },
            body="null",
            callback=self.parse_recent,
        )

    def parse_recent(self, response):
        # The response is an HTML table with PDF links
        # Find the "All SBIMF Schemes" factsheet first (combined)
        links = response.css('a[href$=".pdf"], a[href*=".pdf?"]')
        
        all_schemes_link = None
        first_link = None
        
        for link in links:
            href = link.attrib.get("href", "")
            text = link.css("::text").get("").strip()
            
            if not first_link and text:
                first_link = (text, href)
            
            if "all-sbimf" in href.lower() or "all sbimf" in text.lower():
                all_schemes_link = (text, href)
                break

        chosen = all_schemes_link or first_link
        if not chosen:
            self.logger.error("No factsheet links found!")
            return

        text, href = chosen
        pdf_url = response.urljoin(href)
        title = text or "SBI MF Factsheet"

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
            r"d:\OCR\OCR\Scraped Factsheets", "sbi-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "sbi-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
