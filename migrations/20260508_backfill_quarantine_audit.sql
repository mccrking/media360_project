-- Migration: backfill quarantine_audit for existing quarantined articles
-- Idempotent and safe to rerun.

INSERT INTO quarantine_audit (article_id, action, performed_by, reason)
SELECT a.article_id, 'mark', 'system', 'retroactive-backfill'
FROM articles_detail a
WHERE a.quarantine = TRUE
  AND NOT EXISTS (
      SELECT 1
      FROM quarantine_audit q
      WHERE q.article_id = a.article_id
        AND q.action = 'mark'
        AND q.reason = 'retroactive-backfill'
  );