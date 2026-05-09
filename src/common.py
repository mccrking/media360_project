from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_LAKE_ROOT = Path(os.getenv("DATA_LAKE_ROOT", PROJECT_ROOT / "data_lake"))
GOVERNANCE_ROOT = Path(os.getenv("GOVERNANCE_ROOT", PROJECT_ROOT / "governance"))


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_sources_config() -> list[dict[str, Any]]:
    sources_file = PROJECT_ROOT / "config" / "sources.yml"
    with sources_file.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("sources", [])


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
