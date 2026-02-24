import scrapy


class FactsheetItem(scrapy.Item):
    """Item representing a mutual fund factsheet PDF."""
    fund_name = scrapy.Field()       # e.g., "360-one"
    file_urls = scrapy.Field()       # List of PDF URLs to download
    files = scrapy.Field()           # Populated by FilesPipeline after download
    factsheet_label = scrapy.Field() # e.g., "Fund Factsheet - January"
