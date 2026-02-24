import os
import shutil
from scrapy import signals


class FactsheetRenamePipeline:
    """
    After FilesPipeline downloads a PDF into the default 'full/' subdirectory,
    this pipeline moves it to a fund-specific subfolder with a clean filename.

    Result structure:
        Scraped Factsheets/
            360-one/
                360ONE-MF-February-2026.pdf
    """

    def process_item(self, item, spider):
        files_store = spider.settings.get("FILES_STORE")
        fund_name = item.get("fund_name", "unknown")

        for f in item.get("files", []):
            # Source: FILES_STORE/full/<sha1_hash>.pdf
            src = os.path.join(files_store, f["path"])

            # Extract the original filename from the URL
            original_url = f["url"]
            original_filename = original_url.split("/")[-1]
            # URL-decode the filename
            from urllib.parse import unquote
            original_filename = unquote(original_filename)

            # Destination: FILES_STORE/<fund_name>/<original_filename>
            dest_dir = os.path.join(files_store, fund_name)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, original_filename)

            if os.path.exists(src):
                shutil.move(src, dest)
                spider.logger.info(f"Saved: {dest}")

        return item
