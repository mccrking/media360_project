CREATE TABLE IF NOT EXISTS articles_detail (
    article_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    source TEXT NOT NULL,
    published_at TIMESTAMP,
    url TEXT UNIQUE,
    content TEXT,
    category TEXT,
    ingested_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_source ON articles_detail(source);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles_detail(published_at DESC);

INSERT INTO articles_detail (article_id, title, author, source, published_at, url, category)
VALUES 
    ('art1', 'Iran Nuclear Deal Talks Resume After Months of Silence', 'John Smith', 'BBC News', NOW() - INTERVAL '2 days', 'https://bbc.com/news/iran1', 'politique'),
    ('art2', 'Global Markets Rally on Fed Rate Cut Expectations', 'Jane Doe', 'Reuters World', NOW() - INTERVAL '1 day', 'https://reuters.com/markets/global', 'économie'),
    ('art3', 'Morocco Launches New Tech Initiative', 'Ahmed Hassan', 'Hespress', NOW(), 'https://hespress.com/tech/morocco', 'technologie'),
    ('art4', 'UK Parliament Debates Climate Policy', 'David Brown', 'BBC News', NOW() - INTERVAL '3 hours', 'https://bbc.com/news/climate1', 'environnement'),
    ('art5', 'Tech Giants Post Record Quarterly Earnings', 'Sarah Wilson', 'Reuters World', NOW() - INTERVAL '5 hours', 'https://reuters.com/tech/earnings', 'technologie'),
    ('art6', 'Morocco Announces Education Reforms', 'Fatima Zahra', 'Hespress', NOW() - INTERVAL '8 hours', 'https://hespress.com/education', 'éducation')
ON CONFLICT DO NOTHING;

SELECT COUNT(*) FROM articles_detail;
