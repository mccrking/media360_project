#!/usr/bin/env python3
"""
Continuous ingestion loop: run batch insert every N seconds.
This is the Python-native alternative to ingest_loop.sh.
"""
import os
import sys
import time
from datetime import datetime

# Add project root to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.abspath(os.path.join(_this_dir, ".."))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

# Import the upsert function from run_batch_insert
from run_batch_insert import upsert_articles
from src.scraping.scraper import scrape_latest_articles

INTERVAL_SECONDS = int(os.getenv("INGEST_INTERVAL_SECONDS", "300"))  # 5 minutes default
MAX_ARTICLES_PER_SOURCE = int(os.getenv("INGEST_MAX_ARTICLES", "20"))

def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def ingest_once():
    """Run one ingestion cycle."""
    try:
        log(f"Scraping latest {MAX_ARTICLES_PER_SOURCE} articles per source...")
        recs = scrape_latest_articles(limit_per_source=MAX_ARTICLES_PER_SOURCE)
        log(f"Scraped {len(recs)} articles. Upserting...")
        upsert_articles(recs)
        log(f"Ingestion complete. Next run in {INTERVAL_SECONDS}s")
    except Exception as e:
        log(f"ERROR during ingestion: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run continuous ingestion loop."""
    log(f"Starting ingestion loop (interval={INTERVAL_SECONDS}s, max_articles={MAX_ARTICLES_PER_SOURCE}/src)")
    try:
        while True:
            ingest_once()
            log(f"Sleeping for {INTERVAL_SECONDS} seconds...")
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log("Ingestion loop interrupted by user.")
    except Exception as e:
        log(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
