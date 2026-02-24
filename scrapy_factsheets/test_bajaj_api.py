"""Decode Bajaj AMC AJAX response - find PDF paths."""
import requests
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bajajamc.com/downloads",
    "X-Requested-With": "XMLHttpRequest",
}

data = {
    "view_name": "downloads_disclosure",
    "view_display_id": "block_15",
    "view_args": "",
    "view_path": "/quicktabs/ajax/downloads_disclosure_tabs/5",
    "view_dom_id": "6627c392682d112f5b2600a52094f74c1b0a6dc54f11bfa2b1dde2043ab42fb3",
    "pager_element": "0",
    "term_node_tid_depth": "1349",
    "_drupal_ajax": "1",
    "ajax_page_state[theme]": "custom_theme_v2",
}

resp = requests.post("https://www.bajajamc.com/views/ajax", data=data, headers=headers, timeout=15)
raw = resp.text

# Decode JSON unicode escapes to get actual HTML
decoded = raw.encode().decode('unicode_escape', errors='replace')

# Find context around factsheet_january
for match in re.finditer(r'factsheet.{0,300}', decoded, re.IGNORECASE):
    print(f"--- Match at {match.start()} ---")
    print(match.group()[:300])
    print()

# Also find any .pdf references
print("=== All .pdf references ===")
for match in re.finditer(r'[^\s"<>]{0,200}\.pdf', decoded, re.IGNORECASE):
    print(f"  {match.group()}")
