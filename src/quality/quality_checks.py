from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.common import DATA_LAKE_ROOT, GOVERNANCE_ROOT, ensure_dir, now_utc_iso


def run_quality_checks(min_content_chars: int = 200) -> Path:
    silver_path = DATA_LAKE_ROOT / "silver" / "articles_silver.parquet"
    if not silver_path.exists():
        raise RuntimeError("Silver dataset not found")

    df = pd.read_parquet(silver_path)
    total = max(len(df), 1)

    no_title = int(df["title"].fillna("").str.strip().eq("").sum())
    missing_date = int(pd.to_datetime(df["published_at"], errors="coerce").isna().sum())
    short_content = int(df["content_final"].fillna("").str.len().lt(min_content_chars).sum())

    report = {
        "generated_at": now_utc_iso(),
        "record_count": int(len(df)),
        "tests": {
            "article_sans_titre": no_title,
            "date_manquante": missing_date,
            "contenu_trop_court": short_content,
        },
        "dimensions": {
            "completude": round(100 * (1 - (no_title + missing_date) / (2 * total)), 2),
            "coherence": round(100 * (1 - short_content / total), 2),
            "validite": round(100 * (1 - (no_title + missing_date + short_content) / (3 * total)), 2),
        },
    }

    out_dir = ensure_dir(GOVERNANCE_ROOT)
    out_path = out_dir / "quality_report_latest.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Quality report generated: {out_path}")
    return out_path


if __name__ == "__main__":
    run_quality_checks()
