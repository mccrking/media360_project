#!/usr/bin/env python3
"""Scrape latest articles and insert/upsert into articles_detail table."""
from __future__ import annotations

import os
import sys
from typing import Any

try:
    # Ensure project root is on sys.path so `src` package imports work when running inside container
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    _proj_root = os.path.abspath(os.path.join(_this_dir, ".."))
    if _proj_root not in sys.path:
        sys.path.insert(0, _proj_root)

    from src.scraping.scraper import scrape_latest_articles
except Exception as e:
    print("Error importing scraper:", e)
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import execute_values
except Exception as e:
    print("psycopg2 not available:", e)
    sys.exit(1)

import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "news_dw")
DB_USER = os.getenv("POSTGRES_USER", "news")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "news")


def upsert_articles(records: list[dict[str, Any]]):
    if not records:
        print("No records to insert")
        return

    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()

    sql = (
        "INSERT INTO articles_detail (article_id, title, author, source, published_at, url, canonical_url, content, category, ingested_at, quarantine) VALUES %s "
        "ON CONFLICT (article_id) DO UPDATE SET "
        "title = EXCLUDED.title, author = EXCLUDED.author, source = EXCLUDED.source, published_at = EXCLUDED.published_at, "
        "url = EXCLUDED.url, canonical_url = EXCLUDED.canonical_url, content = EXCLUDED.content, category = EXCLUDED.category, ingested_at = EXCLUDED.ingested_at, quarantine = EXCLUDED.quarantine;"
    )

    # prepare values and detect previous quarantine state
    article_ids = [r.get("article_id") for r in records if r.get("article_id")]
    prev_map: dict[str, bool] = {}
    if article_ids:
        # fetch existing quarantine flags
        cur.execute("SELECT article_id, quarantine FROM articles_detail WHERE article_id = ANY(%s)", (article_ids,))
        for aid, q in cur.fetchall():
            prev_map[aid] = bool(q)

    values = []
    audits: list[tuple[str, str, str]] = []  # (article_id, action, reason)

    # heuristics helpers
    def quarantine_reasons(article: dict[str, Any]) -> list[str]:
        reasons: list[str] = []

        title = str(article.get("title", "") or "").strip()
        url = str(article.get("url", "") or "").strip()
        canonical_url = str(article.get("canonical_url", "") or "").strip()
        source = str(article.get("source", "") or "").lower()
        content = str(article.get("content", "") or "").strip()

        validation_url = canonical_url or url
        if not validation_url:
            reasons.append("url_missing")
            return reasons

        if not validation_url.startswith(("http://", "https://")):
            reasons.append("url_invalid_scheme")
            return reasons

        try:
            parsed = urlparse(validation_url)
        except Exception:
            reasons.append("url_parse_error")
            return reasons

        host = parsed.netloc.lower()
        path = parsed.path.lower()

        if not title:
            reasons.append("title_missing")
        elif len(title) < 8:
            reasons.append("title_too_short")

        nav_blacklist = ("register", "sign in", "signin", "sign up", "login", "home page", "read more")
        if title and any(word in title.lower() for word in nav_blacklist):
            reasons.append("title_generic")

        if title:
            upper_ratio = sum(1 for c in title if c.isupper()) / max(len(title), 1)
            punct_ratio = sum(1 for c in title if c in "!?.,:;-") / max(len(title), 1)
            if upper_ratio > 0.80 and len(title) > 5:
                reasons.append("title_all_caps")
            if punct_ratio > 0.30:
                reasons.append("title_overpunctuated")

        if content and len(content) < 80 and len(title) < 25:
            reasons.append("content_sparse")

        if "bbc" in source:
            if "bbc.com" not in host:
                reasons.append("url_domain_mismatch")
            if path and not path.startswith("/news/"):
                reasons.append("url_path_unexpected")
        elif "hespress" in source:
            if "hespress" not in host:
                reasons.append("url_domain_mismatch")
            if path and not path.endswith(".html"):
                reasons.append("url_path_unexpected")
        elif "reuters" in source:
            if "reuters.com" not in host:
                reasons.append("url_domain_mismatch")
            if path and not any(token in path for token in ("/world/", "/business/", "/markets/", "/technology/", "/legal/", "/sports/", "/breakingviews/", "/video/", "/pictures/", "/live/")):
                reasons.append("url_path_unexpected")

        return reasons

    for r in records:
        reasons = quarantine_reasons(r)
        quarantine_flag = bool(reasons)

        aid = r.get("article_id")
        prev_q = prev_map.get(aid)
        # record audit if state changes (existing row) or if new row is inserted and quarantined
        if aid:
            if prev_q is not None and prev_q != quarantine_flag:
                action = "mark" if quarantine_flag else "unmark"
                audits.append((aid, action, ";".join(reasons)[:200] if reasons else "heuristic-change"))
            elif prev_q is None and quarantine_flag:
                # new article inserted and flagged as quarantined on initial ingest
                audits.append((aid, "mark", ";".join(reasons)[:200] if reasons else "initial-ingest"))

        values.append(
            (
                r.get("article_id"),
                r.get("title"),
                r.get("author"),
                r.get("source"),
                r.get("published_at"),
                r.get("url"),
                r.get("canonical_url"),
                r.get("content"),
                r.get("category"),
                r.get("scraped_at"),
                quarantine_flag,
            )
        )

    try:
        logging.info("Upserting %d articles", len(values))
        execute_values(cur, sql, values, page_size=100)
        # insert audit rows if any
        if audits:
            audit_sql = "INSERT INTO quarantine_audit (article_id, action, reason) VALUES %s"
            execute_values(cur, audit_sql, audits, page_size=100)
            logging.info("Inserted %d audit rows", len(audits))
        conn.commit()
        logging.info("Upsert complete: %d articles", len(values))
    except Exception as e:
        conn.rollback()
        logging.exception("Error upserting articles: %s", e)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    recs = scrape_latest_articles(limit_per_source=20)
    print(f"Scraped {len(recs)} articles")
    upsert_articles(recs)
