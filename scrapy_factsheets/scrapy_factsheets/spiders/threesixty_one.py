import scrapy
from scrapy_factsheets.items import FactsheetItem


class ThreeSixtyOneSpider(scrapy.Spider):
    """
    Spider to download the latest factsheet from 360 ONE Mutual Fund.

    Source page: https://www.360.one/asset-management/mutualfund/downloads/factsheets/
    Actual content (iframe): https://archive.iiflmf.com/downloads/factsheets

    Downloads only the LATEST Direct Plan (non-Regular) factsheet PDF.
    """

    name = "threesixty_one"
    start_urls = ["https://archive.iiflmf.com/downloads/factsheets"]

    def parse(self, response):
        # Find all PDF download links on the page
        pdf_links = response.css('a[href$=".pdf"]')

        latest_direct_plan_url = None
        latest_label = None

        for link in pdf_links:
            href = link.attrib.get("href", "")
            text = link.css("::text").get("").strip()

            # Only consider links under /sites/mf/files/ (actual factsheet PDFs)
            # This skips navigation, KYC, and other misc PDF links
            if "/sites/mf/files/" not in href:
                continue

            # Skip "Regular Plan" factsheets — we want Direct Plan only
            if "Regular" in text or "Regular" in href:
                continue

            # The first matching PDF link is the latest one
            # (page is ordered newest-first)
            if href.endswith(".pdf"):
                latest_direct_plan_url = response.urljoin(href)
                latest_label = text
                break

        if latest_direct_plan_url:
            self.logger.info(
                f"Found latest factsheet: {latest_label} -> {latest_direct_plan_url}"
            )

            item = FactsheetItem()
            item["fund_name"] = "360-one"
            item["file_urls"] = [latest_direct_plan_url]
            item["factsheet_label"] = latest_label
            yield item
        else:
            self.logger.warning("No factsheet PDF found on the page!")
