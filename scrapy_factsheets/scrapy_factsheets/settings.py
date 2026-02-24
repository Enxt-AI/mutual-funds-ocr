BOT_NAME = "scrapy_factsheets"

SPIDER_MODULES = ["scrapy_factsheets.spiders"]
NEWSPIDER_MODULE = "scrapy_factsheets.spiders"

# Obey robots.txt
ROBOTSTXT_OBEY = False

# Configure a user agent to avoid blocks
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 4

# Download delay between requests (be polite)
DOWNLOAD_DELAY = 1

# Enable the Files Pipeline for PDF downloads
ITEM_PIPELINES = {
    "scrapy.pipelines.files.FilesPipeline": 1,
    "scrapy_factsheets.pipelines.FactsheetRenamePipeline": 200,
}

# Base directory where downloaded files will be stored
# FilesPipeline will create a "full/" subdirectory inside this path
FILES_STORE = r"d:\OCR\OCR\Scraped Factsheets"

# Disable Scrapy's default logging noise
LOG_LEVEL = "INFO"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
