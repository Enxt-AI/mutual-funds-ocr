"""
Gemini 2.5 Flash Factsheet Extractor
=====================================
Converts each PDF page to an image, uploads via Google Files API,
and sends to Gemini 2.5 Flash for structured data extraction.

Usage:
    python gemini_extractor.py                     # Process all 42 AMCs
    python gemini_extractor.py --amc ppfas axis    # Process specific AMCs
    python gemini_extractor.py --force              # Re-process even if output exists
"""

import os
import sys
import json
import time
import argparse
import tempfile
import traceback
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types
import fitz  # PyMuPDF


# ─── Configuration ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
FACTSHEETS_DIR = BASE_DIR / "Factsheets"
OUTPUT_DIR = BASE_DIR / "website" / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash"

# Rendering settings
DPI = 250  # High DPI for best extraction quality

# Rate-limit settings
MAX_RETRIES = 5
BASE_DELAY = 10  # seconds

# ─── Extraction Prompt ───────────────────────────────────────────────
EXTRACTION_PROMPT = """You are an expert mutual fund analyst. Analyze this factsheet page image and extract ALL information visible on the page.

Return a JSON object with the following structure. Only include fields that are actually visible on this page. If a field is not present on this page, omit it entirely (do NOT include null values for missing fields).

```json
{
  "schemes": [
    {
      "fund_name": "Full scheme name exactly as shown",
      "fund_type": "Open-ended / Close-ended",
      "scheme_type": "e.g. Open-ended Equity Scheme",
      "category": "e.g. Large Cap Fund, Flexi Cap Fund, Liquid Fund, ELSS, etc.",
      "investment_objective": "Full text of investment objective",
      "benchmark": "Benchmark index name",
      "inception_date": "Date as shown on factsheet",
      "plans_offered": "Direct, Regular, etc.",
      "plan_type": "Direct or Regular",
      "option": "Growth or IDCW",

      "isin": "ISIN code if shown (e.g. INF209KB01234)",
      "amfi_code": "AMFI scheme code if shown",
      "fund_standard_name": "Legal or standard fund name if different from display name",
      "registrar": "Registrar name (e.g. CAMS, KFintech) if shown",

      "nav": 123.45,
      "nav_date": "Date as shown",
      "aum_crores": 12345.67,
      "monthly_avg_aum": 12345.67,
      "expense_ratio": 1.23,
      "exit_load": "Full exit load text as shown",
      "min_sip": 500,
      "min_lumpsum": 5000,
      "min_additional": 1000,
      "min_redemption": 500,

      "sip_available": true,
      "swp_available": true,
      "stp_available": true,

      "risk_level": "Low / Moderately Low / Moderate / Moderately High / High / Very High",
      "morningstar_rating": 4,

      "fund_managers": [
        {
          "name": "Manager Name",
          "qualification": "MBA, CFA, etc.",
          "managing_since": "Date or text as shown",
          "experience": "Years of experience if mentioned",
          "other_schemes_managed": "Other schemes if listed"
        }
      ],

      "returns": [
        {
          "period": "1Y",
          "fund_return": 12.34,
          "benchmark_return": 11.22,
          "category_avg_return": 10.50
        }
      ],

      "equity_holdings": [
        {
          "name": "Company Name",
          "sector": "Sector/Industry",
          "weight_pct": 5.67,
          "market_value_cr": 123.45,
          "quantity": 100000
        }
      ],

      "debt_holdings": [
        {
          "name": "Instrument Name",
          "instrument_type": "G-Sec / Corporate Bond / CP / CD / etc.",
          "rating": "AAA / AA+ / etc.",
          "weight_pct": 3.45,
          "market_value_cr": 56.78,
          "maturity_date": "Date if shown"
        }
      ],

      "sector_allocation": {
        "Sector Name": 12.34
      },

      "asset_allocation": {
        "Equity": 65.0,
        "Debt": 25.0,
        "Cash & Equivalents": 10.0
      },

      "market_cap_allocation": {
        "Large Cap": 60.0,
        "Mid Cap": 25.0,
        "Small Cap": 15.0
      },

      "composition_by_rating": {
        "AAA & Equivalent": 45.0,
        "AA+ & Equivalent": 30.0,
        "Sovereign": 25.0
      },

      "instrument_composition": {
        "Government Securities": 30.0,
        "Corporate Bonds": 40.0,
        "Money Market": 20.0,
        "Cash & Cash Equivalents": 10.0
      },

      "maturity_profile": {
        "0-1 Year": 20.0,
        "1-3 Years": 30.0,
        "3-7 Years": 35.0,
        "7+ Years": 15.0
      },

      "debt_indicators": {
        "ytm": 7.5,
        "modified_duration": 3.2,
        "macaulay_duration": 3.5,
        "average_maturity": 4.1,
        "residual_maturity": 4.5,
        "annualised_portfolio_ytm": 7.8
      },

      "risk_metrics": {
        "alpha": 1.5,
        "beta": 0.85,
        "sharpe_ratio": 1.2,
        "sortino_ratio": 1.8,
        "standard_deviation": 12.5,
        "r_squared": 0.92,
        "treynor_ratio": 10.5,
        "information_ratio": 0.45,
        "max_drawdown": -15.2,
        "tracking_error": 3.2
      },

      "sip_returns": [
        {
          "period": "1Y",
          "total_invested": 12000,
          "market_value": 13500,
          "return_pct": 12.5
        }
      ],

      "stamp_duty": "0.005%",
      "lock_in_period": "3 years for ELSS",
      "dividend_history": [],
      "turnover_ratio": 45.6,
      "portfolio_turnover": "percentage or ratio if shown",

      "portfolio_stats": {
        "pe_ratio": 25.3,
        "pb_ratio": 4.1,
        "dividend_yield": 1.5,
        "roe": 18.5,
        "roa": 8.2,
        "avg_market_cap_cr": 150000,
        "equity_style": "Large Growth / Large Blend / Mid Value / etc."
      }
    }
  ],

  "amc_info": {
    "amc_name": "AMC Full Name",
    "factsheet_date": "Month Year of the factsheet",
    "total_aum": 123456.78,
    "registered_office": "Address if shown",
    "website": "URL if shown"
  },

  "page_type": "fund_detail / holdings / performance / overview / summary / other",
  "raw_tables": [],
  "additional_info": {}
}
```

CRITICAL INSTRUCTIONS:
1. Extract EVERY piece of data visible on this page — do not skip anything
2. For returns, include ALL periods shown (1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, SI — whatever is present)
3. For holdings, include ALL stocks/bonds shown, not just top 10
4. Percentages should be numbers (12.34 not "12.34%")
5. Currency values should be numbers in crores unless specified otherwise
6. If multiple schemes are shown on one page, include all of them in the schemes array
7. For return periods, normalize to: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, SI (Since Inception)
8. If you see "Direct Plan" or "Regular Plan" info, extract the Direct Plan data preferentially
9. Pay attention to tables, charts, pie charts, bar charts — extract data from ALL visual elements
10. Return ONLY valid JSON, no markdown formatting or explanation

Return ONLY the JSON object, nothing else."""


# ─── Helper Functions ─────────────────────────────────────────────────

def pdf_to_images(pdf_path: Path) -> list[Path]:
    """Convert each page of a PDF to a PNG image. Returns list of image paths."""
    doc = fitz.open(str(pdf_path))
    image_paths = []
    temp_dir = tempfile.mkdtemp(prefix="factsheet_")

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render at high DPI for best OCR quality
        mat = fitz.Matrix(DPI / 72, DPI / 72)
        pix = page.get_pixmap(matrix=mat)
        img_path = Path(temp_dir) / f"page_{page_num + 1:03d}.png"
        pix.save(str(img_path))
        image_paths.append(img_path)

    doc.close()
    return image_paths


def upload_to_gemini(image_path: Path) -> object:
    """Upload an image file via Google Files API and wait for it to be active."""
    for attempt in range(MAX_RETRIES):
        try:
            uploaded = client.files.upload(file=image_path)

            # Poll until file is ACTIVE
            max_wait = 30
            waited = 0
            while uploaded.state.name == "PROCESSING" and waited < max_wait:
                time.sleep(1)
                waited += 1
                uploaded = client.files.get(name=uploaded.name)

            if uploaded.state.name != "ACTIVE":
                raise RuntimeError(f"File upload failed — state: {uploaded.state.name}")

            return uploaded

        except Exception as e:
            delay = BASE_DELAY * (2 ** attempt)
            if attempt < MAX_RETRIES - 1:
                print(f"\n      Upload error (attempt {attempt + 1}): {e}")
                print(f"      Retrying in {delay}s...", end=" ", flush=True)
                time.sleep(delay)
            else:
                raise


def _try_repair_json(text: str) -> dict | None:
    """Attempt to repair truncated JSON by closing unclosed braces/brackets."""
    if not text:
        return None

    try:
        # First, try as-is
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try closing unclosed strings, arrays, and objects
    repaired = text.rstrip()

    # If we're inside a string, close it
    # Count unescaped quotes
    in_string = False
    for i, ch in enumerate(repaired):
        if ch == '"' and (i == 0 or repaired[i - 1] != '\\'):
            in_string = not in_string
    if in_string:
        repaired += '"'

    # Count unclosed braces and brackets
    stack = []
    in_str = False
    for i, ch in enumerate(repaired):
        if ch == '"' and (i == 0 or repaired[i - 1] != '\\'):
            in_str = not in_str
        if in_str:
            continue
        if ch in ('{', '['):
            stack.append(ch)
        elif ch == '}' and stack and stack[-1] == '{':
            stack.pop()
        elif ch == ']' and stack and stack[-1] == '[':
            stack.pop()

    # Remove any trailing comma before closing
    repaired = repaired.rstrip().rstrip(',')

    # Close all unclosed braces/brackets in reverse order
    for opener in reversed(stack):
        if opener == '{':
            repaired += '}'
        elif opener == '[':
            repaired += ']'

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def extract_page_with_gemini(uploaded_file) -> dict:
    """Send a single uploaded image to Gemini 2.5 Flash for extraction."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type=uploaded_file.mime_type,
                            ),
                            types.Part.from_text(text=EXTRACTION_PROMPT),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=65536,
                    response_mime_type="application/json",
                ),
            )

            text = response.text
            if text is None:
                # Empty response — likely rate limit or model overload, wait longer
                wait = 30 * (attempt + 1)
                print(f"      Empty response (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait}s...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)
                    continue
                raise RuntimeError("Gemini returned empty response after all retries")
            text = text.strip()

            # Clean up markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            return json.loads(text)

        except json.JSONDecodeError as e:
            print(f"      JSON parse error (attempt {attempt + 1}): {e}")
            # Try to repair truncated JSON before retrying
            repaired = _try_repair_json(text)
            if repaired is not None:
                print(f"      ✅ Repaired truncated JSON successfully")
                return repaired
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)  # Short delay, then retry with fresh API call
            else:
                print(f"      Returning raw text as fallback")
                return {"raw_text": text, "parse_error": str(e)}

        except Exception as e:
            delay = BASE_DELAY * (2 ** attempt)
            print(f"      API error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"      Retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise


def cleanup_uploaded_file(uploaded_file):
    """Delete an uploaded file from Google Files API."""
    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass  # Best-effort cleanup


def merge_page_results(page_results: list[dict]) -> dict:
    """Merge per-page extraction results into a single AMC-level result."""
    merged = {
        "schemes": [],
        "amc_info": {},
        "pages_processed": len(page_results),
    }

    seen_schemes = {}  # fund_name -> index in merged.schemes

    for page_data in page_results:
        if not isinstance(page_data, dict):
            continue

        # Merge AMC info
        if "amc_info" in page_data and page_data["amc_info"]:
            for key, val in page_data["amc_info"].items():
                if val is not None and val != "" and val != {}:
                    merged["amc_info"][key] = val

        # Merge schemes
        for scheme in page_data.get("schemes", []):
            fund_name = scheme.get("fund_name", "")
            if not fund_name:
                continue

            # Check if we've already seen this scheme
            name_key = fund_name.lower().strip()
            if name_key in seen_schemes:
                # Merge into existing scheme data
                idx = seen_schemes[name_key]
                existing = merged["schemes"][idx]
                _deep_merge_scheme(existing, scheme)
            else:
                seen_schemes[name_key] = len(merged["schemes"])
                merged["schemes"].append(scheme)

    return merged


def _deep_merge_scheme(existing: dict, new: dict):
    """Merge new scheme data into existing, preferring non-empty values."""
    for key, val in new.items():
        if val is None or val == "" or val == {} or val == []:
            continue

        if key not in existing or existing[key] is None or existing[key] == "" or existing[key] == {} or existing[key] == []:
            existing[key] = val
        elif isinstance(val, list) and isinstance(existing[key], list):
            # For lists (holdings, returns, managers), merge intelligently
            if key in ("equity_holdings", "debt_holdings"):
                # Add holdings that aren't already there (by name)
                existing_names = {h.get("name", "").lower() for h in existing[key] if h}
                for item in val:
                    if not item or not isinstance(item, dict):
                        continue
                    item_name = (item.get("name") or "").lower()
                    if item_name and item_name not in existing_names:
                        existing[key].append(item)
                        existing_names.add(item_name)
            elif key == "returns":
                # Merge returns by period
                existing_periods = {r.get("period") for r in existing[key] if r}
                for item in val:
                    if not item or not isinstance(item, dict):
                        continue
                    if item.get("period") not in existing_periods:
                        existing[key].append(item)
            elif key == "fund_managers":
                # Merge managers by name
                existing_names = {m.get("name", "").lower() for m in existing[key] if m}
                for item in val:
                    if not item or not isinstance(item, dict):
                        continue
                    item_name = (item.get("name") or "").lower()
                    if item_name and item_name not in existing_names:
                        existing[key].append(item)
                    elif item_name:
                        # Update existing manager with more detail
                        for em in existing[key]:
                            if em and em.get("name", "").lower() == item_name:
                                for mk, mv in item.items():
                                    if mv and not em.get(mk):
                                        em[mk] = mv
            else:
                # For other lists, extend if new items
                existing[key].extend(val)
        elif isinstance(val, dict) and isinstance(existing[key], dict):
            # Merge dict values
            for dk, dv in val.items():
                if dv is not None and (dk not in existing[key] or existing[key][dk] is None):
                    existing[key][dk] = dv


# ─── Main Processing ─────────────────────────────────────────────────

CHECKPOINT_DIR = OUTPUT_DIR / ".checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)


def process_amc(amc_folder: Path, force: bool = False) -> dict | None:
    """Process a single AMC's factsheet PDF with per-page checkpointing."""
    amc_slug = amc_folder.name
    output_file = OUTPUT_DIR / f"{amc_slug}.json"
    checkpoint_file = CHECKPOINT_DIR / f"{amc_slug}_pages.json"

    # Skip if already fully processed
    if output_file.exists() and not force:
        print(f"  ⏭ Already processed, skipping (use --force to re-process)")
        return json.loads(output_file.read_text(encoding="utf-8"))

    # If forcing, also clear checkpoint
    if force and checkpoint_file.exists():
        checkpoint_file.unlink()

    # Find the PDF
    pdfs = list(amc_folder.glob("*.pdf"))
    if not pdfs:
        print(f"  ❌ No PDF found in {amc_folder}")
        return None

    pdf_path = pdfs[0]
    print(f"  📄 PDF: {pdf_path.name}")

    # Load existing checkpoint (page results already extracted)
    checkpoint_data = {}
    if checkpoint_file.exists():
        try:
            checkpoint_data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            checkpoint_data = {}

    completed_pages = checkpoint_data.get("pages", {})  # {"1": {...}, "2": {...}, ...}
    if completed_pages:
        print(f"  🔄 Resuming — {len(completed_pages)} pages already done")

    # Convert PDF to images
    print(f"  🖼 Converting PDF to images...")
    image_paths = pdf_to_images(pdf_path)
    total_pages = len(image_paths)
    print(f"  📸 {total_pages} pages")

    # Process each page
    for i, img_path in enumerate(image_paths):
        page_num = i + 1
        page_key = str(page_num)

        # Skip already checkpointed pages
        if page_key in completed_pages:
            schemes_count = len(completed_pages[page_key].get("schemes", []))
            print(f"    Page {page_num}/{total_pages}... ⏭ (cached, {schemes_count} scheme{'s' if schemes_count != 1 else ''})")
            continue

        print(f"    Page {page_num}/{total_pages}...", end=" ", flush=True)

        try:
            # Upload via Files API
            uploaded = upload_to_gemini(img_path)

            # Extract with Gemini
            result = extract_page_with_gemini(uploaded)

            # Count schemes found
            schemes_count = len(result.get("schemes", []))
            print(f"✅ ({schemes_count} scheme{'s' if schemes_count != 1 else ''})")

            # Cleanup uploaded file
            cleanup_uploaded_file(uploaded)

            # Save checkpoint immediately
            completed_pages[page_key] = result
            checkpoint_data["pages"] = completed_pages
            checkpoint_data["total_pages"] = total_pages
            checkpoint_data["source_pdf"] = pdf_path.name
            checkpoint_file.write_text(
                json.dumps(checkpoint_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            # Small delay between pages to respect rate limits
            if i < len(image_paths) - 1:
                time.sleep(1)

        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()
            completed_pages[page_key] = {"error": str(e), "page": page_num}
            # Still save checkpoint so we know this page had an error
            checkpoint_data["pages"] = completed_pages
            checkpoint_file.write_text(
                json.dumps(checkpoint_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    # Cleanup temp images
    for img_path in image_paths:
        try:
            os.remove(img_path)
        except OSError:
            pass

    # Merge all page results (in page order)
    page_results = [completed_pages[str(p)] for p in range(1, total_pages + 1) if str(p) in completed_pages]
    print(f"  🔗 Merging {len(page_results)} pages...")
    merged = merge_page_results(page_results)
    merged["source_pdf"] = pdf_path.name
    merged["amc_slug"] = amc_slug
    merged["extracted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    # Save final output (local backup)
    output_file.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  💾 Saved locally: {output_file.name} ({len(merged['schemes'])} schemes)")

    # Upload to S3
    if not os.getenv("NO_S3"):
        try:
            import boto3
            s3 = boto3.client(
                "s3",
                region_name=os.getenv("AWS_REGION", "ap-south-1"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
            bucket = os.getenv("S3_BUCKET_NAME", "mutual-funds-ocr-data")
            s3_key = f"funds/{amc_slug}.json"
            s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=json.dumps(merged, indent=2, ensure_ascii=False),
                ContentType="application/json",
            )
            print(f"  ☁️  Uploaded to S3: s3://{bucket}/{s3_key}")
        except Exception as e:
            print(f"  ⚠️  S3 upload failed: {e}")

    # Cleanup checkpoint now that final output is saved
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    return merged


def main():
    parser = argparse.ArgumentParser(description="Extract factsheet data using Gemini 2.5 Flash")
    parser.add_argument("--amc", nargs="*", help="Specific AMC folder names to process (default: all)")
    parser.add_argument("--force", action="store_true", help="Re-process even if output exists")
    args = parser.parse_args()

    print("=" * 60)
    print("  Gemini 2.5 Flash — Factsheet Extractor")
    print("=" * 60)
    print(f"  Model:  {MODEL}")
    print(f"  Source: {FACTSHEETS_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
    print()

    # Determine which AMCs to process
    if args.amc:
        amc_folders = []
        for name in args.amc:
            folder = FACTSHEETS_DIR / name
            if folder.is_dir():
                amc_folders.append(folder)
            else:
                print(f"⚠ AMC folder not found: {name}")
    else:
        amc_folders = sorted([f for f in FACTSHEETS_DIR.iterdir() if f.is_dir()])

    print(f"  Processing {len(amc_folders)} AMC(s)\n")

    results_summary = {}
    for i, folder in enumerate(amc_folders):
        amc_name = folder.name
        print(f"[{i + 1}/{len(amc_folders)}] {amc_name}")

        try:
            result = process_amc(folder, force=args.force)
            if result:
                scheme_count = len(result.get("schemes", []))
                results_summary[amc_name] = {"status": "OK", "schemes": scheme_count}
            else:
                results_summary[amc_name] = {"status": "SKIPPED"}
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            traceback.print_exc()
            results_summary[amc_name] = {"status": "FAILED", "error": str(e)}

        print()

    # Print summary
    print("=" * 60)
    print("  EXTRACTION SUMMARY")
    print("=" * 60)
    total_schemes = 0
    for amc, info in results_summary.items():
        status = info["status"]
        schemes = info.get("schemes", 0)
        total_schemes += schemes
        emoji = "✅" if status == "OK" else "⏭" if status == "SKIPPED" else "❌"
        print(f"  {emoji} {amc}: {status}" + (f" ({schemes} schemes)" if schemes else ""))

    print(f"\n  Total schemes extracted: {total_schemes}")
    print(f"  Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
