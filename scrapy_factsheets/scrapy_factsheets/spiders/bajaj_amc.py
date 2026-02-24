"""Bajaj Finserv AMC factsheet spider.

The Bajaj AMC site is Drupal-powered with quicktabs for downloads.
The factsheet tab (index 5) uses Drupal Views AJAX:

1. GET /quicktabs/ajax/downloads_disclosure_tabs/5 to get the dropdown
2. Parse dropdown to find the latest FY and months with term IDs
3. POST /views/ajax with the latest month's term_node_tid_depth
4. If empty, fallback to previous months until a PDF is found
5. Extract the PDF URL from the decoded HTML
"""
import scrapy
import json
import re
from scrapy_factsheets.items import FactsheetItem


class BajajAMCSpider(scrapy.Spider):
    name = "bajaj_amc"
    allowed_domains = ["www.bajajamc.com"]

    VIEWS_AJAX_URL = "https://www.bajajamc.com/views/ajax"
    QUICKTABS_AJAX_URL = "https://www.bajajamc.com/quicktabs/ajax/downloads_disclosure_tabs/5"

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.bajajamc.com/downloads",
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            self.QUICKTABS_AJAX_URL,
            callback=self.parse_tab,
            method="GET",
        )

    def parse_tab(self, response):
        """Parse quicktab AJAX response to build list of months to try."""
        try:
            commands = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error("Failed to parse quicktab JSON")
            return

        html_content = ""
        for cmd in commands:
            if cmd.get("command") == "insert" and "quicktabs" in cmd.get("selector", ""):
                html_content = cmd.get("data", "")
                break

        if not html_content:
            self.logger.error("No HTML content found in quicktab response")
            return

        # Parse dropdown options
        option_pattern = re.compile(
            r'<option\s+value="(\d+)"\s+data-parent="([^"]*)"[^>]*>\s*([^<]+?)\s*</option>',
            re.DOTALL
        )
        options = option_pattern.findall(html_content)

        if not options:
            self.logger.error("No dropdown options found")
            return

        # Build year -> months mapping
        years = {}
        months = {}
        for term_id, parent_id, label in options:
            if not parent_id:
                years[term_id] = label.strip()
            else:
                months.setdefault(parent_id, []).append((term_id, label.strip()))

        # Find latest FY
        latest_year_id = max(years.keys(), key=lambda x: int(x))
        latest_year_label = years[latest_year_id]
        self.logger.info(f"Latest FY: {latest_year_label} (term {latest_year_id})")

        # Get all months for the latest FY, sorted by term ID descending (latest first)
        year_months = sorted(
            months.get(latest_year_id, []),
            key=lambda x: int(x[0]),
            reverse=True,
        )

        if not year_months:
            self.logger.error(f"No months found for FY {latest_year_label}")
            return

        self.logger.info(f"Months available: {[m[1] for m in year_months]}")

        # Try months in reverse order (latest first), pass remaining as meta
        first_id, first_name = year_months[0]
        remaining = year_months[1:]

        yield self._make_views_request(
            first_id, first_name, latest_year_label, remaining
        )

    def _make_views_request(self, term_id, month_name, year_label, remaining_months):
        """Create a Views AJAX request for a specific month."""
        formdata = {
            "view_name": "downloads_disclosure",
            "view_display_id": "block_15",
            "view_args": "",
            "view_path": "/quicktabs/ajax/downloads_disclosure_tabs/5",
            "view_dom_id": "6627c392682d112f5b2600a52094f74c1b0a6dc54f11bfa2b1dde2043ab42fb3",
            "pager_element": "0",
            "term_node_tid_depth": term_id,
            "_drupal_ajax": "1",
            "ajax_page_state[theme]": "custom_theme_v2",
        }

        return scrapy.FormRequest(
            self.VIEWS_AJAX_URL,
            formdata=formdata,
            callback=self.parse_factsheet,
            cb_kwargs={
                "month_label": month_name,
                "year_label": year_label,
                "remaining_months": remaining_months,
            },
        )

    def parse_factsheet(self, response, month_label, year_label, remaining_months):
        """Extract PDF URL from the Views AJAX response."""
        # Unescape JSON slash encoding (\/ -> /) so paths become normal
        raw = response.text.replace('\\/', '/')

        # Find PDF paths: /sites/default/files/...pdf
        pdf_matches = re.findall(
            r'(/sites/default/files/[^\s"<>,]+?\.pdf)',
            raw, re.IGNORECASE
        )

        if not pdf_matches:
            self.logger.warning(
                f"No PDF found for {month_label} {year_label}, "
                f"trying previous month..."
            )
            if remaining_months:
                next_id, next_name = remaining_months[0]
                yield self._make_views_request(
                    next_id, next_name, year_label, remaining_months[1:]
                )
            else:
                self.logger.error("No factsheets found for any month!")
            return

        # Use the first PDF match
        pdf_path = pdf_matches[0]
        # Ensure it starts with /
        if not pdf_path.startswith('/'):
            pdf_path = '/' + pdf_path

        pdf_url = f"https://www.bajajamc.com{pdf_path}"

        self.logger.info(f"Found factsheet for {month_label} {year_label}")
        self.logger.info(f"PDF URL: {pdf_url}")

        item = FactsheetItem()
        item["fund_name"] = "bajaj-amc"
        item["file_urls"] = [pdf_url]
        item["factsheet_label"] = f"Bajaj Finserv Factsheet {month_label} {year_label}"
        yield item
