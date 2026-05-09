from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from confluent_kafka import Producer

from src.common import DATA_LAKE_ROOT, now_utc_iso, write_jsonl
from src.scraping.scraper import scrape_latest_articles

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_RAW", "news_articles_raw")


def _kafka_producer() -> Producer | None:
    try:
        return Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    except Exception:
        return None


def run_batch_ingestion() -> Path:
    articles = scrape_latest_articles(limit_per_source=25)
    run_ts = datetime.utcnow()

    out_dir = (
        DATA_LAKE_ROOT
        / "bronze"
        / "batch"
        / f"date={run_ts.strftime('%Y-%m-%d')}"
        / f"hour={run_ts.strftime('%H')}"
    )
    out_file = out_dir / "articles_raw.jsonl"

    for article in articles:
        article["ingestion_mode"] = "batch"
        article["ingested_at"] = now_utc_iso()

    write_jsonl(out_file, articles)

    producer = _kafka_producer()
    if producer is not None:
        for article in articles:
            producer.produce(KAFKA_TOPIC, json.dumps(article, ensure_ascii=False).encode("utf-8"))
        producer.flush(10)

    print(f"Batch ingestion complete: {len(articles)} articles -> {out_file}")
    return out_file


if __name__ == "__main__":
    run_batch_ingestion()
