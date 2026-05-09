-- Migration: add canonical_url to articles_detail and ensure quarantine_audit exists
ALTER TABLE articles_detail ADD COLUMN IF NOT EXISTS canonical_url TEXT;

CREATE TABLE IF NOT EXISTS quarantine_audit (
    id SERIAL PRIMARY KEY,
    article_id TEXT NOT NULL,
    action TEXT NOT NULL,
    performed_by TEXT DEFAULT 'system',
    reason TEXT,
    performed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quarantine_audit_article ON quarantine_audit(article_id);
