CREATE TABLE IF NOT EXISTS articles_by_day (
    published_day DATE,
    articles_count INTEGER
);

CREATE TABLE IF NOT EXISTS articles_by_theme (
    theme TEXT,
    articles_count INTEGER
);

CREATE TABLE IF NOT EXISTS articles_by_country (
    source_country TEXT,
    articles_count INTEGER
);

CREATE TABLE IF NOT EXISTS articles_by_source (
    source TEXT,
    articles_count INTEGER
);

CREATE TABLE IF NOT EXISTS top_keywords (
    keyword TEXT,
    frequency INTEGER
);
