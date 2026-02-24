"""Deeper probe for Angel One — search all links, script tags, and data attributes."""
import scrapy
import re
import json


class AngelOneProbeSpider(scrapy.Spider):
    """Probe spider to discover factsheet PDF URLs on Angel One downloads page."""

    name = "angel_one_probe"
    start_urls = ["https://www.angelonemf.com/downloads"]

    custom_settings = {
        "ITEM_PIPELINES": {},  # Disable file download pipelines
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    }

    def parse(self, response):
        self.logger.info(f"Page length: {len(response.text)} chars")

        # 1. Find ALL PDF links
        all_pdfs = response.css('a[href$=".pdf"]::attr(href)').getall()
        self.logger.info(f"Total PDF links (<a> tags): {len(all_pdfs)}")
        for pdf in all_pdfs:
            if 'factsheet' in pdf.lower():
                self.logger.info(f"  FACTSHEET: {pdf}")

        # 2. Search entire HTML source for factsheet patterns
        factsheet_urls = re.findall(
            r'https?://[^\s"\'<>]*factsheet[^\s"\'<>]*\.pdf',
            response.text, re.IGNORECASE
        )
        self.logger.info(f"Factsheet URLs in raw HTML: {len(factsheet_urls)}")
        for url in set(factsheet_urls):
            self.logger.info(f"  {url}")

        # 3. Look for JSON data embedded in script tags
        scripts = response.css('script::text').getall()
        self.logger.info(f"Script tags: {len(scripts)}")
        for i, script in enumerate(scripts):
            if 'factsheet' in script.lower():
                self.logger.info(f"  Script #{i} mentions 'factsheet' ({len(script)} chars)")
                # Extract a snippet around the factsheet mention
                idx = script.lower().find('factsheet')
                snippet = script[max(0, idx-100):idx+200]
                self.logger.info(f"  ...{snippet}...")

        # 4. Look for Next.js data / __NEXT_DATA__
        next_data = response.css('script#__NEXT_DATA__::text').get()
        if next_data:
            self.logger.info("Found __NEXT_DATA__!")
            try:
                data = json.loads(next_data)
                # Search for factsheet in the JSON
                data_str = json.dumps(data)
                if 'factsheet' in data_str.lower():
                    self.logger.info("  __NEXT_DATA__ contains 'factsheet'!")
                    # Find factsheet URLs in this data
                    fs_urls = re.findall(r'https?://[^"]*factsheet[^"]*\.pdf', data_str, re.IGNORECASE)
                    for u in fs_urls:
                        self.logger.info(f"    {u}")
                else:
                    self.logger.info("  __NEXT_DATA__ does NOT contain 'factsheet'")
            except json.JSONDecodeError:
                self.logger.info("  Failed to parse __NEXT_DATA__")

        # 5. Look for data attributes containing URLs
        data_attrs = re.findall(r'data-[a-z-]+=["\'](https?://[^"\']+\.pdf)["\']', response.text, re.IGNORECASE)
        self.logger.info(f"PDF links in data- attributes: {len(data_attrs)}")
        for attr in data_attrs:
            self.logger.info(f"  {attr}")

        # 6. Search for CMS upload paths
        cms_paths = re.findall(r'cms\.angelonemf\.com[^\s"\'<>]*', response.text, re.IGNORECASE)
        self.logger.info(f"CMS paths found: {len(cms_paths)}")
        for path in set(cms_paths)[:20]:
            self.logger.info(f"  {path}")
