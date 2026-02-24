"""ITI Mutual Fund factsheet spider.

ITI AMC uses AES-CBC encrypted API requests. The encryption params
(extracted from the Angular main bundle) are:
  Key: aar6tzij8o1snaar  (16 bytes)
  IV:  0123456789ABCDEF  (16 bytes)
  Mode: CBC, Padding: PKCS7

The request body is: {"eData": AES_encrypt(JSON.stringify(payload))}
The response body is: {"eData": AES_encrypt(JSON.stringify(data))}

Endpoint: POST https://itiamc.com/jeeth/api/v1/catalog/getDocumentsByType
Payload:  {"type": "downloads"}
Response: {data: {documentList: [{topic, returnList: [{id, url, fileName, year}]}]}}
"""
import scrapy
import json
import os
import base64
from urllib.parse import unquote
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from scrapy_factsheets.items import FactsheetItem


class ItiMFSpider(scrapy.Spider):
    name = "iti_mf"
    allowed_domains = ["itiamc.com", "www.itiamc.com"]

    AES_KEY = b"aar6tzij8o1snaar"
    AES_IV = b"0123456789ABCDEF"

    API_URL = "https://itiamc.com/jeeth/api/v1/catalog/getDocumentsByType"

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.itiamc.com",
            "Referer": "https://www.itiamc.com/",
        },
    }

    def _encrypt(self, plaintext: str) -> str:
        padder = sym_padding.PKCS7(128).padder()
        padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV))
        enc = cipher.encryptor()
        ct = enc.update(padded) + enc.finalize()
        return base64.b64encode(ct).decode("utf-8")

    def _decrypt(self, ciphertext: str) -> str:
        ct = base64.b64decode(ciphertext)
        cipher = Cipher(algorithms.AES(self.AES_KEY), modes.CBC(self.AES_IV))
        dec = cipher.decryptor()
        padded = dec.update(ct) + dec.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        pt = unpadder.update(padded) + unpadder.finalize()
        return pt.decode("utf-8")

    def start_requests(self):
        payload = json.dumps({"type": "downloads"})
        body = json.dumps({"eData": self._encrypt(payload)})
        yield scrapy.Request(
            self.API_URL,
            method="POST",
            body=body,
            callback=self.parse_api,
            dont_filter=True,
        )

    def parse_api(self, response):
        resp = json.loads(response.text)
        decrypted = json.loads(self._decrypt(resp["eData"]))

        doc_list = decrypted.get("data", {}).get("documentList", [])
        self.logger.info(f"Found {len(doc_list)} document topics")

        # Find the Factsheet topic
        for topic in doc_list:
            if topic.get("topic", "").lower() == "factsheet":
                items = topic.get("returnList", [])
                self.logger.info(f"Factsheet topic has {len(items)} items")
                if not items:
                    return

                latest = items[0]
                pdf_url = latest.get("url", "")
                title = latest.get("fileName", "")
                self.logger.info(f"Latest: {title}")
                self.logger.info(f"PDF URL: {pdf_url}")

                yield scrapy.Request(
                    pdf_url,
                    callback=self.save_pdf,
                    meta={"title": title},
                    dont_filter=True,
                )
                return

        self.logger.error("No 'Factsheet' topic found in documentList")

    def save_pdf(self, response):
        title = response.meta["title"]

        if response.status != 200:
            self.logger.error(f"PDF download failed: {response.status}")
            return

        save_dir = os.path.join(
            r"d:\OCR\OCR\Scraped Factsheets", "iti-mutual-fund"
        )
        os.makedirs(save_dir, exist_ok=True)

        filename = unquote(response.url.split("/")[-1])
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.body)

        self.logger.info(f"Saved: {filepath}")

        item = FactsheetItem()
        item["fund_name"] = "iti-mutual-fund"
        item["file_urls"] = []
        item["files"] = [{"path": filepath, "url": response.url}]
        item["factsheet_label"] = title
        yield item
