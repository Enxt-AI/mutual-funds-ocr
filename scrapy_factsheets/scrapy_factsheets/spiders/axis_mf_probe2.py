"""Deep probe Axis MF Angular app for exact API configuration."""
import scrapy
import re


class AxisMFProbe2Spider(scrapy.Spider):
    """Deep probe to find exact baseUrl and factsheet API config."""

    name = "axis_mf_probe2"
    start_urls = ["https://www.axismf.com/main-es2015.61f794a94928664fd8ec.js"]

    custom_settings = {
        "ITEM_PIPELINES": {},
    }

    def parse(self, response):
        text = response.text

        # 1. Find environment/config object with baseUrl
        # Angular environment configs look like: {production:true,baseUrl:"...",...}
        base_url_patterns = re.findall(
            r'baseUrl\s*:\s*["\']([^"\']+)["\']', text
        )
        self.logger.info(f"baseUrl values: {base_url_patterns}")

        # 2. Find detailUrl 
        detail_url_patterns = re.findall(
            r'detailUrl\s*:\s*["\']([^"\']+)["\']', text
        )
        self.logger.info(f"detailUrl values: {detail_url_patterns}")
        
        # 3. Find cmsURL 
        cms_url_patterns = re.findall(
            r'cmsURL\s*:\s*["\']([^"\']+)["\']', text
        )
        self.logger.info(f"cmsURL values: {cms_url_patterns}")

        # 4. Find GET_FACTSHEET constant definition
        factsheet_const = re.findall(
            r'GET_FACTSHEET\s*[:=]\s*["\']([^"\']+)["\']', text
        )
        self.logger.info(f"GET_FACTSHEET constant: {factsheet_const}")

        # 5. Find broader context around GET_FACTSHEET
        idx = text.find('GET_FACTSHEET')
        if idx > -1:
            # Get surrounding 500 chars
            start = max(0, idx - 200)
            end = min(len(text), idx + 300)
            context = text[start:end]
            self.logger.info(f"Context around GET_FACTSHEET: {context}")

        # 6. Find context around getFactsheetData
        idx2 = text.find('getFactsheetData')
        if idx2 > -1:
            start = max(0, idx2 - 100)
            end = min(len(text), idx2 + 400)
            context2 = text[start:end]
            self.logger.info(f"Context around getFactsheetData: {context2}")

        # 7. Find all http/https URLs that could be API base URLs
        api_urls = re.findall(
            r'["\']https?://[^"\']*(?:axis|axismf|kfintech)[^"\']*["\']',
            text
        )
        self.logger.info(f"Axis/KFintech URLs found: {len(api_urls)}")
        for u in list(set(api_urls))[:20]:
            self.logger.info(f"  {u}")

        # 8. Find appUrl
        app_url_patterns = re.findall(
            r'appUrl\s*:\s*["\']([^"\']+)["\']', text
        )
        self.logger.info(f"appUrl values: {app_url_patterns}")

        # 9. Find any URL with 'factsheet' in it
        factsheet_urls = re.findall(
            r'https?://[^"\'>\s]+factsheet[^"\'>\s]*', text, re.IGNORECASE
        )
        self.logger.info(f"Factsheet URLs: {len(factsheet_urls)}")
        for u in list(set(factsheet_urls))[:10]:
            self.logger.info(f"  {u}")

        # 10. Find download-related API endpoints  
        download_endpoints = re.findall(
            r'["\']([^"\']*download[^"\']*factsheet[^"\']*|[^"\']*factsheet[^"\']*download[^"\']*)["\']',
            text, re.IGNORECASE
        )
        self.logger.info(f"Download+factsheet combined: {download_endpoints}")
