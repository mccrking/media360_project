-- Médaillon Architecture - Silver Layer Tables
-- Create Silver layer tables for cleaned/normalized data

-- Silver layer main table
CREATE TABLE IF NOT EXISTS articles_silver (
    article_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    title_normalized TEXT,
    author TEXT,
    content TEXT,
    content_clean TEXT,
    content_length INTEGER,
    word_count INTEGER,
    source TEXT NOT NULL,
    category TEXT,
    detected_language VARCHAR(10),
    published_at TIMESTAMP,
    url TEXT,
    canonical_url TEXT,
    quarantine BOOLEAN DEFAULT FALSE,
    data_quality_score DECIMAL(3,2),
    silver_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scraped_at TIMESTAMP,
    CONSTRAINT silver_quality CHECK (data_quality_score >= 0 AND data_quality_score <= 1)
);

CREATE INDEX idx_silver_source ON articles_silver(source);
CREATE INDEX idx_silver_language ON articles_silver(detected_language);
CREATE INDEX idx_silver_timestamp ON articles_silver(silver_timestamp);
CREATE INDEX idx_silver_quality ON articles_silver(data_quality_score);

-- Audit trail for transformations
CREATE TABLE IF NOT EXISTS transformation_audit (
    id SERIAL PRIMARY KEY,
    article_id TEXT NOT NULL REFERENCES articles_silver(article_id) ON DELETE CASCADE,
    transformation_type VARCHAR(50),
    input_value TEXT,
    output_value TEXT,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transformation_timestamp TIMESTAMP
);

CREATE INDEX idx_transform_article_id ON transformation_audit(article_id);
CREATE INDEX idx_transform_type ON transformation_audit(transformation_type);
