#!/usr/bin/env python3
"""
Optional automatic purge: remove articles quarantined > N days ago.
Run periodically (e.g., daily) to maintain a clean database.
"""
import os
import sys
import psycopg2
from datetime import datetime, timedelta

DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "news_dw")
DB_USER = os.getenv("POSTGRES_USER", "news")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "news")

QUARANTINE_RETENTION_DAYS = int(os.getenv("QUARANTINE_RETENTION_DAYS", "7"))

def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def purge_old_quarantined():
    """Remove articles marked quarantined for > QUARANTINE_RETENTION_DAYS."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, 
            user=DB_USER, password=DB_PASS
        )
        cur = conn.cursor()
        
        cutoff_date = datetime.utcnow() - timedelta(days=QUARANTINE_RETENTION_DAYS)
        log(f"Removing articles quarantined before {cutoff_date.isoformat()}")
        
        # Delete from audit first (FK constraint)
        cur.execute(
            "DELETE FROM quarantine_audit WHERE article_id IN "
            "(SELECT article_id FROM articles_detail WHERE quarantine = TRUE AND ingested_at < %s)",
            (cutoff_date,)
        )
        audit_deleted = cur.rowcount
        
        # Then delete from articles_detail
        cur.execute(
            "DELETE FROM articles_detail WHERE quarantine = TRUE AND ingested_at < %s",
            (cutoff_date,)
        )
        articles_deleted = cur.rowcount
        
        conn.commit()
        log(f"Purged: {articles_deleted} articles, {audit_deleted} audit records")
        
    except Exception as e:
        log(f"ERROR during purge: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    log(f"Starting purge (retention={QUARANTINE_RETENTION_DAYS} days)")
    purge_old_quarantined()
