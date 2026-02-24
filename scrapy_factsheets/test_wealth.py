"""Deep parse scheme-documents tab for factsheets."""
import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

r = requests.get("https://www.wealthcompanyamc.in/api/literature-forms", headers=headers, timeout=15)
data = r.json()

# Get scheme-documents tab
scheme_tab = data["data"]["mainTab"][2]
print(f"Tab: {scheme_tab['title']}, slug: {scheme_tab['slug']}")
print(f"Keys: {list(scheme_tab.keys())}")

# Dump all nested structure
def dump_deep(obj, depth=0, max_depth=5):
    indent = "  " * depth
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                if isinstance(v, list):
                    print(f"{indent}{k}: list[{len(v)}]")
                else:
                    print(f"{indent}{k}: dict")
                dump_deep(v, depth+1, max_depth)
            else:
                val = str(v)
                if len(val) > 100:
                    val = val[:100] + "..."
                if '.pdf' in val.lower() or 'factsheet' in val.lower():
                    print(f"{indent}{k}: *** {val} ***")
                elif depth <= 3:
                    print(f"{indent}{k}: {val}")
    elif isinstance(obj, list) and depth < max_depth:
        for i, item in enumerate(obj[:5]):
            print(f"{indent}[{i}]:")
            dump_deep(item, depth+1, max_depth)
        if len(obj) > 5:
            print(f"{indent}... ({len(obj)} items total)")

dump_deep(scheme_tab, max_depth=6)
