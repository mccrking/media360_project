from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from src.common import DATA_LAKE_ROOT, ensure_dir

STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "will", "into", "about", "dans",
    "avec", "pour", "sur", "plus", "sont", "une", "des", "les", "est", "que", "qui", "par", "pas",
}

THEME_KEYWORDS = {
    "politique": ["election", "government", "president", "parliament", "minister", "politique"],
    "economie": ["market", "economy", "inflation", "business", "finance", "economie"],
    "sport": ["football", "match", "team", "league", "sport"],
    "technologie": ["ai", "technology", "digital", "software", "internet", "tech"],
}


def _infer_theme(text: str) -> str:
    lower = (text or "").lower()
    for theme, words in THEME_KEYWORDS.items():
        if any(w in lower for w in words):
            return theme
    return "autre"


def _keywords(series: pd.Series, top_n: int = 25) -> pd.DataFrame:
    counts: Counter[str] = Counter()
    for text in series.fillna(""):
        words = re.findall(r"[a-zA-Z]{4,}", text.lower())
        words = [w for w in words if w not in STOPWORDS]
        counts.update(words)

    rows = [{"keyword": word, "frequency": freq} for word, freq in counts.most_common(top_n)]
    return pd.DataFrame(rows)


def _warehouse_conn():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "news_dw")
    user = os.getenv("POSTGRES_USER", "news")
    pwd = os.getenv("POSTGRES_PASSWORD", "news")
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd)


def _load_table(conn, table_name: str, columns: list[str], rows: list[tuple]) -> None:
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_name}")
        if rows:
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES %s"
            execute_values(cur, insert_sql, rows)


def run_to_gold(load_to_dw: bool = True) -> dict[str, Path]:
    silver_path = DATA_LAKE_ROOT / "silver" / "articles_silver.parquet"
    if not silver_path.exists():
        raise RuntimeError("Silver dataset not found")

    df = pd.read_parquet(silver_path)
    df["published_day"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True).dt.date
    df["theme"] = (df["title"].fillna("") + " " + df["content_final"].fillna("")) .map(_infer_theme)

    by_day = df.groupby("published_day", dropna=False).size().reset_index(name="articles_count")
    by_source = df.groupby("source", dropna=False).size().reset_index(name="articles_count")
    by_theme = df.groupby("theme", dropna=False).size().reset_index(name="articles_count")
    by_country = df.groupby("source_country", dropna=False).size().reset_index(name="articles_count")
    top_keywords = _keywords(df["content_final"])

    gold_dir = ensure_dir(DATA_LAKE_ROOT / "gold")
    outputs = {
        "articles_by_day": gold_dir / "articles_by_day.parquet",
        "articles_by_source": gold_dir / "articles_by_source.parquet",
        "articles_by_theme": gold_dir / "articles_by_theme.parquet",
        "articles_by_country": gold_dir / "articles_by_country.parquet",
        "top_keywords": gold_dir / "top_keywords.parquet",
    }

    by_day.to_parquet(outputs["articles_by_day"], index=False)
    by_source.to_parquet(outputs["articles_by_source"], index=False)
    by_theme.to_parquet(outputs["articles_by_theme"], index=False)
    by_country.to_parquet(outputs["articles_by_country"], index=False)
    top_keywords.to_parquet(outputs["top_keywords"], index=False)

    if load_to_dw:
        conn = _warehouse_conn()
        try:
            _load_table(
                conn,
                "articles_by_day",
                ["published_day", "articles_count"],
                list(by_day[["published_day", "articles_count"]].itertuples(index=False, name=None)),
            )
            _load_table(
                conn,
                "articles_by_theme",
                ["theme", "articles_count"],
                list(by_theme[["theme", "articles_count"]].itertuples(index=False, name=None)),
            )
            _load_table(
                conn,
                "articles_by_country",
                ["source_country", "articles_count"],
                list(by_country[["source_country", "articles_count"]].itertuples(index=False, name=None)),
            )
            _load_table(
                conn,
                "articles_by_source",
                ["source", "articles_count"],
                list(by_source[["source", "articles_count"]].itertuples(index=False, name=None)),
            )
            _load_table(
                conn,
                "top_keywords",
                ["keyword", "frequency"],
                list(top_keywords[["keyword", "frequency"]].itertuples(index=False, name=None)),
            )
            conn.commit()
        finally:
            conn.close()

    print("Gold layer complete and loaded to warehouse")
    return outputs


if __name__ == "__main__":
    run_to_gold()
