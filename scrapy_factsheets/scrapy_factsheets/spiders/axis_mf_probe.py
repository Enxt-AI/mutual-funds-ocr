"""Probe Axis MF Angular app to find factsheet API endpoints."""
import scrapy
import re
import json


class AxisMFProbeSpider(scrapy.Spider):
    """Probe spider to discover factsheet API endpoints on Axis MF."""

    name = "axis_mf_probe"
    start_urls = ["https://www.axismf.com/main-es2015.61f794a94928664fd8ec.js"]

    custom_settings = {
        "ITEM_PIPELINES": {},
    }

    def parse(self, response):
        text = response.text
        self.logger.info(f"JS bundle size: {len(text)} chars")

        # Search for API URL patterns
        api_patterns = re.findall(
            r'["\']([^"\']*(?:factsheet|download|pdf|api)[^"\']*)["\']',
            text, re.IGNORECASE
        )
        
        # Filter for interesting ones
        interesting = [
            p for p in api_patterns 
            if any(kw in p.lower() for kw in ['factsheet', 'download', '.pdf'])
            and len(p) < 200
            and not p.startswith('function')
        ]
        
        self.logger.info(f"Interesting API patterns: {len(interesting)}")
        for p in list(set(interesting))[:30]:
            self.logger.info(f"  {p}")

        # Also search for environment/API base URL
        env_patterns = re.findall(
            r'["\']([^"\']*(?:apiUrl|baseUrl|apiBase|serviceUrl|environment)[^"\']*)["\']',
            text, re.IGNORECASE
        )
        self.logger.info(f"Environment patterns: {len(env_patterns)}")
        for p in list(set(env_patterns))[:10]:
            self.logger.info(f"  {p}")

        # Search for URL-like patterns containing /api/ or /services/
        url_patterns = re.findall(
            r'["\'](/(?:api|services|rest|content|cms|assets)/[^"\']+)["\']',
            text, re.IGNORECASE
        )
        self.logger.info(f"URL patterns with /api|services|rest/: {len(url_patterns)}")
        for p in list(set(url_patterns))[:20]:
            self.logger.info(f"  {p}")
