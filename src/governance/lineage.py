from __future__ import annotations

import json
from pathlib import Path

from src.common import DATA_LAKE_ROOT, GOVERNANCE_ROOT, ensure_dir, now_utc_iso


def generate_lineage() -> Path:
    lineage = {
        "generated_at": now_utc_iso(),
        "pipelines": [
            {
                "name": "news_pipeline",
                "source": "RSS + Web Scraping",
                "layers": {
                    "bronze": str(DATA_LAKE_ROOT / "bronze"),
                    "silver": str(DATA_LAKE_ROOT / "silver" / "articles_silver.parquet"),
                    "gold": str(DATA_LAKE_ROOT / "gold"),
                    "warehouse": "postgres.news_dw",
                },
            }
        ],
    }

    out_dir = ensure_dir(GOVERNANCE_ROOT)
    out_path = out_dir / "lineage.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(lineage, f, ensure_ascii=False, indent=2)

    print(f"Lineage generated: {out_path}")
    return out_path


if __name__ == "__main__":
    generate_lineage()
