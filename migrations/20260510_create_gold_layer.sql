-- Médaillon Architecture - Gold Layer Tables
-- Create Gold layer tables for analytical aggregations

-- Articles aggregated by source
CREATE TABLE IF NOT EXISTS articles_by_source (
    source TEXT PRIMARY KEY,
    articles_count INTEGER NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Articles aggregated by category
CREATE TABLE IF NOT EXISTS articles_by_category (
    category TEXT PRIMARY KEY,
    articles_count INTEGER NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Top keywords extraction
CREATE TABLE IF NOT EXISTS top_keywords (
    keyword TEXT PRIMARY KEY,
    frequency INTEGER NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily trends table
CREATE TABLE IF NOT EXISTS daily_article_trends (
    trend_date DATE NOT NULL,
    source TEXT NOT NULL,
    articles_count INTEGER,
    avg_word_count INTEGER,
    avg_quality_score DECIMAL(3,2),
    PRIMARY KEY (trend_date, source)
);

-- Analytics summary (hourly)
CREATE TABLE IF NOT EXISTS analytics_summary (
    summary_timestamp TIMESTAMP PRIMARY KEY,
    total_articles INTEGER,
    articles_today INTEGER,
    quarantined_articles INTEGER,
    unique_sources INTEGER,
    avg_quality_score DECIMAL(3,2),
    languages_detected INTEGER
);

-- Create indexes for performance
CREATE INDEX idx_trends_date ON daily_article_trends(trend_date);
CREATE INDEX idx_summary_timestamp ON analytics_summary(summary_timestamp);
CREATE INDEX idx_keywords_frequency ON top_keywords(frequency DESC);
