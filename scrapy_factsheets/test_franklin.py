"""Extract PDF URL from Franklin Templeton factsheet API."""
import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

base = "https://www.franklintempletonindia.com"
url = f"{base}/api/literature/v1/documents?channel=en-in&contentGrouping=FUND-FACTSHEETS"

r = requests.get(url, headers=headers, timeout=15)
data = r.json()

docs = data.get('document', [])
print(f"Total documents: {len(docs)}")

# Show first 3 documents with all keys
for i, doc in enumerate(docs[:3]):
    print(f"\n=== Document {i+1} ===")
    print(f"Keys: {list(doc.keys())}")
    print(json.dumps(doc, indent=2)[:2000])
    
# Specifically look for PDF URLs
print("\n\n=== PDF URLs in all documents ===")
for i, doc in enumerate(docs[:10]):
    title = doc.get('dctermsTitle', 'unknown')
    pdf_url = doc.get('pdfUrl', doc.get('pdfURL', doc.get('litPath', doc.get('url', 'NOT FOUND'))))
    doc_type = doc.get('dctermsType', '')
    print(f"  {i+1}. [{doc_type}] {title}")
    # Check all keys containing 'url', 'path', 'link', 'pdf'
    for k, v in doc.items():
        if any(term in k.lower() for term in ['url', 'path', 'link', 'pdf', 'download', 'file']):
            print(f"     {k}: {v}")
