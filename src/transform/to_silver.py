from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from langdetect import detect

from src.common import DATA_LAKE_ROOT, ensure_dir


def _clean_html(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return soup.get_text(" ", strip=True)


def _normalize_text(value: str) -> str:
    value = value or ""
    value = value.replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _detect_language(text: str) -> str:
    try:
        return detect(text) if text else "unknown"
    except Exception:
        return "unknown"


def _read_bronze_records() -> list[dict]:
    records: list[dict] = []
    bronze_root = DATA_LAKE_ROOT / "bronze"
    for path in bronze_root.rglob("*.jsonl"):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def run_to_silver() -> Path:
    records = _read_bronze_records()
    if not records:
        raise RuntimeError("No bronze records found")

    df = pd.DataFrame(records)
    df["content_clean"] = df["content"].fillna("").map(_normalize_text)
    df["content_from_html"] = df["content_html"].fillna("").map(_clean_html)
    df["content_final"] = df.apply(
        lambda r: r["content_clean"] if r["content_clean"] else _normalize_text(r["content_from_html"]), axis=1
    )
    df["title"] = df["title"].fillna("").map(_normalize_text)
    df["author"] = df["author"].fillna("Unknown").map(_normalize_text)
    df["category"] = df["category"].fillna("Unknown").map(_normalize_text)
    df["source"] = df["source"].fillna("Unknown").map(_normalize_text)
    df["language"] = df["content_final"].map(_detect_language)
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)

    df = df.sort_values("scraped_at").drop_duplicates(subset=["url"], keep="last")

    silver_dir = ensure_dir(DATA_LAKE_ROOT / "silver")
    silver_path = silver_dir / "articles_silver.parquet"
    df.to_parquet(silver_path, index=False)

    print(f"Silver layer complete: {len(df)} records -> {silver_path}")
    return silver_path


if __name__ == "__main__":
    run_to_silver()
