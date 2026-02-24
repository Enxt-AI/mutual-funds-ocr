"""JM Financial Mutual Fund factsheet spider.

JM Financial MF uses an AES-256-CBC encrypted API.
  Key: "6fa979f20126cb08aa645a8f495f6d85" (32-char UTF-8 string = 256-bit key)
  IV:  "I8zyA4lVhMCaJ5Kg" (16-char UTF-8 string)

Endpoint: POST https://jmmfapi.jmfinancialmf.com/api/GetFactsheet
Response: {"data": "<AES-encrypted base64>", "statusCode": 0}
Decrypted: [{"FileName": "CMS/downloads/.../Factsheet February 2026.pdf", ...}]
PDF URL:   https://www.jmfinancialmf.com/{FileName}
"""
import scrapy
import json
import os
import base64
from urllib.parse import quote
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from scrapy_factsheets.items import FactsheetItem


class JmFinancialMFSpider(scrapy.Spider):
    name = "jm_financial_mf"
    allowed_domains = [
        "jmmfapi.jmfinancialmf.com",
        "www.jmfinancialmf.com",
        "jmfinancialmf.com",
    ]

    API_URL = "https://jmmfapi.jmfinancialmf.com/api/GetFactsheet"
    BASE_URL = "https://www.jmfinancialmf.com"

    AES_KEY = b"6fa979f20126cb08aa645a8f495f6d85"  # 32 bytes UTF-8 = AES-256
    AES_IV = b"I8zyA4lVhMCaJ5Kg"  # 16 bytes

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.jmfinancialmf.com",
            "Referer": "https://www.jmfinancialmf.com/",
        },
    }

    def _decrypt(self, ciphertext: str) -> str:
        ct = base64.b64decode(ciphertext)
        cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV))
        dec = cipher.decryptor()
        padded = dec.update(ct) + dec.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        pt = unpadder.update(padded) + unpadder.finalize()
        return pt.decode("utf-8")

    def start_requests(self):
        yield scrapy.Request(
            self.API_URL,
            method="POST",
            body="{}",
            callback=self.parse_api,
            dont_filter=True,
        )

    def parse_api(self, response):
        resp = json.loads(response.text)
        decrypted = json.loads(self._decrypt(resp["data"]))

        self.logger.info(f"Found {len(decrypted)} factsheet(s)")

        if not decrypted:
            self.logger.error("No factsheets returned")
            return

        # Take the first (latest) entry
        latest = decrypted[0]
        title = latest.get("Title", "")
        filename = latest.get("FileName", "")

        self.logger.info(f"Latest: {title}")
        self.logger.info(f"File: {filename}")

        # Build full URL (spaces need encoding)
        pdf_url = f"{self.BASE_URL}/{quote(filename, safe='/')}"
        self.logger.info(f"PDF URL: {pdf_url}")

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
            r"d:\OCR\OCR\Scraped Factsheets", "jm-financial-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{title}.pdf".replace("/", "-")
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "jm-financial-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
