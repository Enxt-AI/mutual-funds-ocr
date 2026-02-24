"""
Factsheet Pipeline Orchestrator
================================
Automates the complete factsheet workflow:
  1. Run Scrapy spider to download latest factsheet PDF
  2. Copy PDF from 'Scraped Factsheets/<amc>/' to 'Factsheets/<amc>/'
  3. Run gemini_extractor.py for OCR + JSON generation + S3 upload
  4. Move to next AMC

Checkpoint compatible:
  - Respects gemini_extractor.py's per-page checkpoints by default
  - Saves pipeline-level state to resume after crashes
  - Use --force to re-process everything from scratch

Usage:
    python pipeline.py                        # Process all AMCs (resumes if interrupted)
    python pipeline.py --amc axis-mf sbi-mf   # Process specific AMCs
    python pipeline.py --list                  # List all available AMCs
    python pipeline.py --scrape-only           # Only download, skip OCR
    python pipeline.py --force                 # Re-process, ignoring checkpoints
"""

import os
import sys
import json
import time
import shutil
import glob
import argparse
import subprocess
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
SCRAPED_DIR = BASE_DIR / "Scraped Factsheets"
FACTSHEETS_DIR = Path(os.getenv("FACTSHEETS_PATH", str(BASE_DIR / "Factsheets")))
SCRAPY_PROJECT = BASE_DIR / "scrapy_factsheets"
EXTRACTOR_SCRIPT = BASE_DIR / "gemini_extractor.py"
PIPELINE_STATE_FILE = BASE_DIR / ".pipeline_state.json"


# ─── Spider Registry ────────────────────────────────────────────────
# Maps a human-readable AMC slug to:
#   spider_name:    Scrapy crawler name (used with `scrapy crawl`)
#   scraped_folder: folder name in "Scraped Factsheets/"
#
# The scraped_folder is also used as the AMC slug in Factsheets/ and
# for gemini_extractor.py (--amc flag).

SPIDER_REGISTRY = {
    "360-one": {
        "spider_name": "threesixty_one",
        "scraped_folder": "360-one",
        "display_name": "360 ONE Mutual Fund",
    },
    "aditya-birla-sun-life": {
        "spider_name": "aditya_birla",
        "scraped_folder": "aditya-birla-sun-life",
        "display_name": "Aditya Birla Sun Life MF",
    },
    "angel-one": {
        "spider_name": "angel_one",
        "scraped_folder": "angel-one",
        "display_name": "Angel One Mutual Fund",
    },
    "axis-mf": {
        "spider_name": "axis_mf",
        "scraped_folder": "axis-mf",
        "display_name": "Axis Mutual Fund",
    },
    "bajaj-amc": {
        "spider_name": "bajaj_amc",
        "scraped_folder": "bajaj-amc",
        "display_name": "Bajaj Finserv AMC",
    },
    "bandhan-mf": {
        "spider_name": "bandhan_mf",
        "scraped_folder": "bandhan-mf",
        "display_name": "Bandhan Mutual Fund",
    },
    "baroda-bnp-paribas": {
        "spider_name": "baroda_bnp",
        "scraped_folder": "baroda-bnp-paribas",
        "display_name": "Baroda BNP Paribas MF",
    },
    "canara-robeco": {
        "spider_name": "canara_robeco",
        "scraped_folder": "canara-robeco",
        "display_name": "Canara Robeco MF",
    },
    "capitalmind": {
        "spider_name": "capitalmind",
        "scraped_folder": "capitalmind",
        "display_name": "Capitalmind MF",
    },
    "choice-mf": {
        "spider_name": "choice_mf",
        "scraped_folder": "choice-mf",
        "display_name": "Choice Mutual Fund",
    },
    "dsp-mutual-fund": {
        "spider_name": "dsp_mf",
        "scraped_folder": "dsp-mutual-fund",
        "display_name": "DSP Mutual Fund",
    },
    "edelweiss-mf": {
        "spider_name": "edelweiss_mf",
        "scraped_folder": "edelweiss-mf",
        "display_name": "Edelweiss Mutual Fund",
    },
    "franklin-templeton-mutual-fund": {
        "spider_name": "franklin_templeton_mf",
        "scraped_folder": "franklin-templeton-mutual-fund",
        "display_name": "Franklin Templeton MF",
    },
    "groww-mutual-fund": {
        "spider_name": "groww_mf",
        "scraped_folder": "groww-mutual-fund",
        "display_name": "Groww Mutual Fund",
    },
    "helios-mutual-fund": {
        "spider_name": "helios_mf",
        "scraped_folder": "helios-mutual-fund",
        "display_name": "Helios Mutual Fund",
    },
    "hsbc-mutual-fund": {
        "spider_name": "hsbc_mf",
        "scraped_folder": "hsbc-mutual-fund",
        "display_name": "HSBC Mutual Fund",
    },
    "icici-prudential-mutual-fund": {
        "spider_name": "icici_pru_mf",
        "scraped_folder": "icici-prudential-mutual-fund",
        "display_name": "ICICI Prudential MF",
    },
    "invesco-mutual-fund": {
        "spider_name": "invesco_mf",
        "scraped_folder": "invesco-mutual-fund",
        "display_name": "Invesco Mutual Fund",
    },
    "iti-mutual-fund": {
        "spider_name": "iti_mf",
        "scraped_folder": "iti-mutual-fund",
        "display_name": "ITI Mutual Fund",
    },
    "jio-blackrock-mutual-fund": {
        "spider_name": "jio_blackrock_mf",
        "scraped_folder": "jio-blackrock-mutual-fund",
        "display_name": "Jio BlackRock Mutual Fund",
    },
    "jm-financial-mutual-fund": {
        "spider_name": "jm_financial_mf",
        "scraped_folder": "jm-financial-mutual-fund",
        "display_name": "JM Financial Mutual Fund",
    },
    "kotak-mutual-fund": {
        "spider_name": "kotak_mf",
        "scraped_folder": "kotak-mutual-fund",
        "display_name": "Kotak Mutual Fund",
    },
    "lic-mutual-fund": {
        "spider_name": "lic_mf",
        "scraped_folder": "lic-mutual-fund",
        "display_name": "LIC Mutual Fund",
    },
    "mahindra-manulife-mutual-fund": {
        "spider_name": "mahindra_manulife_mf",
        "scraped_folder": "mahindra-manulife-mutual-fund",
        "display_name": "Mahindra Manulife MF",
    },
    "mirae-asset-mutual-fund": {
        "spider_name": "mirae_asset_mf",
        "scraped_folder": "mirae-asset-mutual-fund",
        "display_name": "Mirae Asset Mutual Fund",
    },
    "navi-mutual-fund": {
        "spider_name": "navi_mf",
        "scraped_folder": "navi-mutual-fund",
        "display_name": "Navi Mutual Fund",
    },
    "nippon-india-mutual-fund": {
        "spider_name": "nippon_india_mf",
        "scraped_folder": "nippon-india-mutual-fund",
        "display_name": "Nippon India Mutual Fund",
    },
    "nj-mutual-fund": {
        "spider_name": "nj_mf",
        "scraped_folder": "nj-mutual-fund",
        "display_name": "NJ Mutual Fund",
    },
    "old-bridge-mutual-fund": {
        "spider_name": "old_bridge_mf",
        "scraped_folder": "old-bridge-mutual-fund",
        "display_name": "Old Bridge Mutual Fund",
    },
    "pgim-india-mutual-fund": {
        "spider_name": "pgim_india_mf",
        "scraped_folder": "pgim-india-mutual-fund",
        "display_name": "PGIM India Mutual Fund",
    },
    "ppfas-mutual-fund": {
        "spider_name": "ppfas_mf",
        "scraped_folder": "ppfas-mutual-fund",
        "display_name": "PPFAS Mutual Fund",
    },
    "quant-mutual-fund": {
        "spider_name": "quant_mf",
        "scraped_folder": "quant-mutual-fund",
        "display_name": "Quant Mutual Fund",
    },
    "quantum-mutual-fund": {
        "spider_name": "quantum_amc",
        "scraped_folder": "quantum-mutual-fund",
        "display_name": "Quantum Mutual Fund",
    },
    "samco-mutual-fund": {
        "spider_name": "samco_mf",
        "scraped_folder": "samco-mutual-fund",
        "display_name": "Samco Mutual Fund",
    },
    "sbi-mutual-fund": {
        "spider_name": "sbi_mf",
        "scraped_folder": "sbi-mutual-fund",
        "display_name": "SBI Mutual Fund",
    },
    "shriram-mutual-fund": {
        "spider_name": "shriram_amc",
        "scraped_folder": "shriram-mutual-fund",
        "display_name": "Shriram Mutual Fund",
    },
    "sundaram-mutual-fund": {
        "spider_name": "sundaram_mf",
        "scraped_folder": "sundaram-mutual-fund",
        "display_name": "Sundaram Mutual Fund",
    },
    "tata-mutual-fund": {
        "spider_name": "tata_mf",
        "scraped_folder": "tata-mutual-fund",
        "display_name": "Tata Mutual Fund",
    },
    "taurus-mutual-fund": {
        "spider_name": "taurus_mf",
        "scraped_folder": "taurus-mutual-fund",
        "display_name": "Taurus Mutual Fund",
    },
    "trust-mutual-fund": {
        "spider_name": "trust_mf",
        "scraped_folder": "trust-mutual-fund",
        "display_name": "Trust Mutual Fund",
    },
    "unifi-mutual-fund": {
        "spider_name": "unifi_mf",
        "scraped_folder": "unifi-mutual-fund",
        "display_name": "Unifi Mutual Fund",
    },
    "uti-mutual-fund": {
        "spider_name": "uti_mf",
        "scraped_folder": "uti-mutual-fund",
        "display_name": "UTI Mutual Fund",
    },
    "wealth-company-amc": {
        "spider_name": "wealth_company_amc",
        "scraped_folder": "wealth-company-amc",
        "display_name": "Wealth Company AMC",
    },
    "whiteoak-capital-amc": {
        "spider_name": "whiteoak_amc",
        "scraped_folder": "whiteoak-capital-amc",
        "display_name": "WhiteOak Capital AMC",
    },
    "zerodha-fund-house": {
        "spider_name": "zerodha_fund_house",
        "scraped_folder": "zerodha-fund-house",
        "display_name": "Zerodha Fund House",
    },
}


# ─── Helper Functions ────────────────────────────────────────────────

def emit(event_type, **kwargs):
    """Print a structured JSON event line for the admin API to parse."""
    payload = {"event": event_type, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), **kwargs}
    print(json.dumps(payload), flush=True)


def run_spider(spider_name: str) -> tuple[bool, str]:
    """Run a Scrapy spider. Returns (success, output_text)."""
    cmd = ["scrapy", "crawl", spider_name]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRAPY_PROJECT),
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Spider timed out after 120 seconds"
    except Exception as e:
        return False, f"Spider error: {e}"


def find_latest_pdf(folder: Path) -> Path | None:
    """Find the most recently modified PDF in a folder."""
    pdfs = list(folder.glob("*.pdf"))
    if not pdfs:
        return None
    # Return the most recently modified PDF
    return max(pdfs, key=lambda p: p.stat().st_mtime)


def copy_pdf_to_factsheets(scraped_folder: Path, amc_slug: str) -> Path | None:
    """Copy the latest PDF from Scraped Factsheets to Factsheets."""
    pdf = find_latest_pdf(scraped_folder)
    if not pdf:
        return None

    dest_dir = FACTSHEETS_DIR / amc_slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Clear any existing PDFs in dest dir
    for existing in dest_dir.glob("*.pdf"):
        existing.unlink()

    dest_path = dest_dir / pdf.name
    shutil.copy2(pdf, dest_path)
    return dest_path


def run_extractor(amc_slug: str, force: bool = False) -> tuple[bool, str]:
    """Run gemini_extractor.py for a specific AMC.
    
    Streams output line-by-line so the admin panel shows page progress.
    By default, respects existing checkpoints:
      - Skips AMCs that already have output JSON
      - Resumes partially processed AMCs from last completed page
    Pass force=True to re-process from scratch.
    """
    cmd = ["python", str(EXTRACTOR_SCRIPT), "--amc", amc_slug]
    if force:
        cmd.append("--force")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,  # Line-buffered
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
        )

        output_lines = []
        start_time = time.time()
        timeout = 1800  # 30 minutes for large PDFs

        for line in iter(proc.stdout.readline, ""):
            line = line.rstrip("\n\r")
            if line:
                output_lines.append(line)
                # Forward to pipeline stdout so admin panel sees it
                print(f"    [OCR] {line}", flush=True)

            if time.time() - start_time > timeout:
                proc.kill()
                output_lines.append(f"TIMEOUT: Killed after {timeout}s")
                return False, "\n".join(output_lines)

        proc.wait()
        return proc.returncode == 0, "\n".join(output_lines)

    except Exception as e:
        return False, f"Extractor error: {e}"


# ─── Pipeline State (for resume) ────────────────────────────────────

def load_pipeline_state() -> dict:
    """Load pipeline state from disk for crash recovery."""
    if PIPELINE_STATE_FILE.exists():
        try:
            return json.loads(PIPELINE_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_pipeline_state(state: dict):
    """Save pipeline state to disk."""
    PIPELINE_STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def clear_pipeline_state():
    """Remove the pipeline state file (called on successful completion)."""
    if PIPELINE_STATE_FILE.exists():
        PIPELINE_STATE_FILE.unlink()


# ─── Main Pipeline ──────────────────────────────────────────────────

def process_amc(amc_slug: str, scrape_only: bool = False, force: bool = False) -> dict:
    """Process a single AMC through the full pipeline."""
    entry = SPIDER_REGISTRY.get(amc_slug)
    if not entry:
        emit("error", amc=amc_slug, message=f"Unknown AMC: {amc_slug}")
        return {"status": "error", "message": f"Unknown AMC: {amc_slug}"}

    spider_name = entry["spider_name"]
    scraped_folder = entry["scraped_folder"]
    display_name = entry["display_name"]

    result = {
        "amc": amc_slug,
        "display_name": display_name,
        "status": "pending",
        "steps": {},
    }

    # Step 1: Run the Scrapy spider
    emit("step_start", amc=amc_slug, step="scrape", display_name=display_name)
    print(f"  🕷  Scraping {display_name} (spider: {spider_name})...", flush=True)

    success, output = run_spider(spider_name)
    result["steps"]["scrape"] = {"success": success, "output_lines": len(output.splitlines())}

    if not success:
        emit("step_done", amc=amc_slug, step="scrape", success=False)
        print(f"  ❌ Spider failed for {display_name}", flush=True)
        # Don't return yet — try to use existing scraped PDF if available
        scraped_dir = SCRAPED_DIR / scraped_folder
        if not scraped_dir.exists() or not find_latest_pdf(scraped_dir):
            result["status"] = "failed"
            result["error"] = "Spider failed and no existing PDF found"
            emit("amc_done", amc=amc_slug, status="failed", error=result["error"])
            return result
        print(f"  ℹ️  Using existing scraped PDF", flush=True)
    else:
        emit("step_done", amc=amc_slug, step="scrape", success=True)
        print(f"  ✅ Spider completed", flush=True)

    # Step 2: Copy PDF to Factsheets
    scraped_dir = SCRAPED_DIR / scraped_folder
    emit("step_start", amc=amc_slug, step="copy")
    pdf_path = copy_pdf_to_factsheets(scraped_dir, amc_slug)

    if not pdf_path:
        result["status"] = "failed"
        result["error"] = f"No PDF found in {scraped_dir}"
        emit("amc_done", amc=amc_slug, status="failed", error=result["error"])
        print(f"  ❌ No PDF found in {scraped_dir}", flush=True)
        return result

    result["steps"]["copy"] = {"success": True, "pdf": pdf_path.name}
    emit("step_done", amc=amc_slug, step="copy", success=True, pdf=pdf_path.name)
    print(f"  📋 Copied: {pdf_path.name}", flush=True)

    if scrape_only:
        result["status"] = "scraped"
        emit("amc_done", amc=amc_slug, status="scraped", pdf=pdf_path.name)
        print(f"  ⏭  Skipping OCR (--scrape-only)", flush=True)
        return result

    # Step 3: Run OCR with gemini_extractor.py
    emit("step_start", amc=amc_slug, step="extract")
    print(f"  🔍 Extracting data with Gemini OCR...", flush=True)

    success, output = run_extractor(amc_slug, force=force)
    result["steps"]["extract"] = {"success": success, "output_lines": len(output.splitlines())}

    if not success:
        result["status"] = "extract_failed"
        result["error"] = "OCR extraction failed"
        emit("amc_done", amc=amc_slug, status="extract_failed", error="OCR failed")
        print(f"  ❌ OCR extraction failed for {display_name}", flush=True)
        # Print last few lines of output for debugging
        for line in output.strip().splitlines()[-5:]:
            print(f"      {line}", flush=True)
        return result

    emit("step_done", amc=amc_slug, step="extract", success=True)
    result["status"] = "done"
    emit("amc_done", amc=amc_slug, status="done")
    print(f"  ✅ {display_name} — pipeline complete!", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description="Factsheet Pipeline Orchestrator")
    parser.add_argument("--amc", nargs="*", help="Specific AMC slugs to process (default: all)")
    parser.add_argument("--list", action="store_true", help="List all registered AMCs and exit")
    parser.add_argument("--scrape-only", action="store_true", help="Only download PDFs, skip OCR")
    parser.add_argument("--force", action="store_true", help="Re-process from scratch, ignoring all checkpoints")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(
            {slug: {"display_name": v["display_name"], "spider": v["spider_name"]}
             for slug, v in sorted(SPIDER_REGISTRY.items())},
            indent=2
        ))
        return

    # Determine which AMCs to process
    if args.amc:
        amc_slugs = []
        for slug in args.amc:
            if slug in SPIDER_REGISTRY:
                amc_slugs.append(slug)
            else:
                print(f"⚠  Unknown AMC slug: {slug}. Use --list to see available AMCs.", flush=True)
    else:
        amc_slugs = sorted(SPIDER_REGISTRY.keys())

    total = len(amc_slugs)
    print(f"\n{'=' * 60}", flush=True)
    print(f"  Factsheet Pipeline — {total} AMC(s)", flush=True)
    print(f"  Mode: {'Scrape Only' if args.scrape_only else 'Full Pipeline (Scrape + OCR + S3)'}", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    emit("pipeline_start", total=total, amcs=amc_slugs,
         mode="scrape_only" if args.scrape_only else "full")

    # Load pipeline state for resume support
    pipeline_state = {} if args.force else load_pipeline_state()
    completed_amcs = set(pipeline_state.get("completed", []))

    results = []
    for i, slug in enumerate(amc_slugs):
        # Skip AMCs already completed in a previous run (crash recovery)
        if slug in completed_amcs and not args.force:
            print(f"\n[{i + 1}/{total}] {SPIDER_REGISTRY[slug]['display_name']} — ⏭ already done (resuming)", flush=True)
            emit("amc_done", amc=slug, status="done")
            results.append({"amc": slug, "status": "done", "display_name": SPIDER_REGISTRY[slug]["display_name"]})
            continue

        print(f"\n[{i + 1}/{total}] {SPIDER_REGISTRY[slug]['display_name']}", flush=True)
        emit("amc_start", amc=slug, index=i + 1, total=total)

        result = process_amc(slug, scrape_only=args.scrape_only, force=args.force)
        results.append(result)

        # Save state after each AMC for crash recovery
        if result["status"] in ("done", "scraped"):
            completed_amcs.add(slug)
            pipeline_state["completed"] = sorted(completed_amcs)
            pipeline_state["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            save_pipeline_state(pipeline_state)

    # Summary
    done = sum(1 for r in results if r["status"] == "done")
    scraped = sum(1 for r in results if r["status"] == "scraped")
    failed = sum(1 for r in results if r["status"] in ("failed", "extract_failed", "error"))

    print(f"\n{'=' * 60}", flush=True)
    print(f"  PIPELINE SUMMARY", flush=True)
    print(f"{'=' * 60}", flush=True)

    for r in results:
        emoji = "✅" if r["status"] in ("done", "scraped") else "❌"
        display = SPIDER_REGISTRY.get(r["amc"], {}).get("display_name", r["amc"])
        error_msg = f" — {r.get('error', '')}" if r.get("error") else ""
        print(f"  {emoji} {display}: {r['status']}{error_msg}", flush=True)

    print(f"\n  Completed: {done}  |  Scraped: {scraped}  |  Failed: {failed}", flush=True)

    emit("pipeline_done", done=done, scraped=scraped, failed=failed, total=total)

    # Clean up state file if everything succeeded (no failures)
    if failed == 0:
        clear_pipeline_state()


if __name__ == "__main__":
    main()
