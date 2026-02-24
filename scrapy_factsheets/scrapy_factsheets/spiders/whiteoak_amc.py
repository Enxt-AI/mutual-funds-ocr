"""White Oak Capital AMC factsheet spider.

White Oak AMC uses a Strapi CMS with GraphQL API at cms.whiteoakamc.com.
The client-side Next.js app queries downloads via Apollo Client.
We query the GraphQL endpoint directly with category="Factsheet" to get
the latest factsheet PDF URL from the download_media_file relation.
"""
import json
import scrapy
import os
from scrapy_factsheets.items import FactsheetItem


class WhiteoakAMCSpider(scrapy.Spider):
    name = "whiteoak_amc"
    allowed_domains = ["cms.whiteoakamc.com", "content.whiteoakamc.com"]

    GRAPHQL_URL = "https://cms.whiteoakamc.com/graphql"

    GRAPHQL_QUERY = """
    query getDownloadsByCategory(
        $category: String
        $start: Int
        $limit: Int
    ) {
        downloads(
            pagination: { start: $start, limit: $limit }
            filters: {
                master_document_category: { value: { eq: $category } }
            }
            sort: "published_date:DESC"
        ) {
            data {
                id
                attributes {
                    title
                    published_date
                    download_media_file {
                        data {
                            id
                            attributes {
                                url
                                ext
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """

    def start_requests(self):
        payload = {
            "query": self.GRAPHQL_QUERY,
            "variables": {
                "category": "Factsheet",
                "start": 0,
                "limit": 10,
            },
        }

        yield scrapy.Request(
            self.GRAPHQL_URL,
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload),
            callback=self.parse_graphql,
            dont_filter=True,
        )

    def parse_graphql(self, response):
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"JSON parse error: {response.text[:200]}")
            return

        if "errors" in data:
            self.logger.error(f"GraphQL errors: {data['errors']}")
            return

        downloads = data.get("data", {}).get("downloads", {}).get("data", [])
        self.logger.info(f"Found {len(downloads)} downloads in Factsheet category")

        # Find the latest factsheet entry with a PDF
        for item in downloads:
            attrs = item.get("attributes", {})
            title = attrs.get("title", "")

            if "factsheet" not in title.lower():
                continue

            media = attrs.get("download_media_file", {}).get("data")
            if not media:
                continue

            media_attrs = media.get("attributes", {})
            pdf_url = media_attrs.get("url", "")

            if not pdf_url:
                continue

            self.logger.info(f"Latest factsheet: {title} -> {pdf_url}")

            yield scrapy.Request(
                pdf_url,
                callback=self.save_pdf,
                meta={"title": title},
                dont_filter=True,
            )
            return  # Only download the latest factsheet

        self.logger.warning("No factsheet PDF found in GraphQL response")

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "whiteoak-capital-amc"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-").replace(":", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath} ({len(response.body)} bytes)")

        item = FactsheetItem()
        item["fund_name"] = "whiteoak-capital-amc"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
