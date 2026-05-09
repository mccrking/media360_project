from __future__ import annotations

import json
import os
from datetime import datetime

from confluent_kafka import Consumer

from src.common import DATA_LAKE_ROOT, append_jsonl, now_utc_iso

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_RAW", "news_articles_raw")


def run_streaming_consumer(max_messages: int = 200, max_idle_polls: int = 10) -> None:
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP,
            "group.id": "news-stream-group",
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([KAFKA_TOPIC])

    consumed = 0
    idle_polls = 0
    try:
        while consumed < max_messages:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                idle_polls += 1
                if idle_polls >= max_idle_polls:
                    break
                continue
            if msg.error():
                continue

            idle_polls = 0

            payload = json.loads(msg.value().decode("utf-8"))
            payload["stream_received_at"] = now_utc_iso()
            payload["ingestion_mode"] = "streaming"

            ts = datetime.utcnow()
            out_file = (
                DATA_LAKE_ROOT
                / "bronze"
                / "streaming"
                / f"date={ts.strftime('%Y-%m-%d')}"
                / f"hour={ts.strftime('%H')}"
                / "articles_stream.jsonl"
            )
            append_jsonl(out_file, payload)
            consumed += 1
    finally:
        consumer.close()

    print(f"Streaming consumer complete: {consumed} messages consumed")


if __name__ == "__main__":
    run_streaming_consumer()
