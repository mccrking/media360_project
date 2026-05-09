"""
Médaillon Architecture Pipeline Scripts
Handles Bronze -> Silver -> Gold transformations
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter
import hashlib
import re

import pandas as pd
from minio import Minio
import sqlalchemy as sa

from src.common import load_sources_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MinIO Config
MINIO_CLIENT = Minio(
    "minio:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

BUCKET_BRONZE = "bronze-articles"
BUCKET_SILVER = "silver-articles"
BUCKET_GOLD = "gold-analytics"

# Database Config
DB_URL = "postgresql+psycopg2://news:news@postgres:5432/news_dw"
ENGINE = sa.create_engine(DB_URL)

def ensure_buckets():
    """Create MinIO buckets if they don't exist."""
    for bucket in [BUCKET_BRONZE, BUCKET_SILVER, BUCKET_GOLD]:
        try:
            MINIO_CLIENT.make_bucket(bucket)
            logger.info(f"Created bucket: {bucket}")
        except:
            logger.info(f"Bucket already exists: {bucket}")


def extract_bronze():
    """
    Bronze Layer: Extract raw articles from RSS feeds
    Store as JSON in MinIO bronze bucket
    """
    logger.info("=== BRONZE LAYER: RAW EXTRACTION ===")
    
    try:
        ensure_buckets()
        from src.scraping.scraper import scrape_latest_articles
        
        # Scrape articles
        articles = scrape_latest_articles(limit_per_source=20)
        logger.info(f"Scraped {len(articles)} articles")
        
        if not articles:
            logger.warning("No articles scraped")
            return 0
        
        # Save to MinIO Bronze (one file per timestamp)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        bronze_file = f"articles_raw_{timestamp}.jsonl"
        
        # Create JSONL content
        content = "\n".join([json.dumps(article, ensure_ascii=False) for article in articles])
        
        # Upload to MinIO
        from io import BytesIO
        MINIO_CLIENT.put_object(
            BUCKET_BRONZE,
            bronze_file,
            BytesIO(content.encode('utf-8')),
            length=len(content),
            content_type="application/jsonl"
        )
        logger.info(f"Uploaded {bronze_file} to Bronze layer")
        
        return len(articles)
    
    except Exception as e:
        logger.error(f"Bronze extraction failed: {e}")
        raise


def _infer_theme(text: str) -> str:
    lower = (text or "").lower()
    theme_keywords = {
        "politique": ["election", "government", "president", "parliament", "minister", "politique"],
        "economie": ["market", "economy", "inflation", "business", "finance", "economie"],
        "sport": ["football", "match", "team", "league", "sport"],
        "technologie": ["ai", "technology", "digital", "software", "internet", "tech"],
    }
    for theme, words in theme_keywords.items():
        if any(word in lower for word in words):
            return theme
    return "autre"


def _top_keywords(series: pd.Series, top_n: int = 100) -> pd.DataFrame:
    stopwords = {
        "the", "and", "for", "with", "this", "that", "from", "have", "will", "into", "about",
        "dans", "avec", "pour", "sur", "plus", "sont", "une", "des", "les", "est", "que",
        "qui", "par", "pas", "au", "du", "de", "la", "le", "et", "en",
    }
    counts: Counter[str] = Counter()
    for text in series.fillna(""):
        words = re.findall(r"[a-zA-Z]{4,}", str(text).lower())
        counts.update(word for word in words if word not in stopwords)
    return pd.DataFrame(
        [{"keyword": word, "frequency": freq} for word, freq in counts.most_common(top_n)]
    )


def transform_silver():
    """
    Silver Layer: Clean, normalize and enrich data
    Remove HTML, normalize text, detect language
    """
    logger.info("=== SILVER LAYER: CLEANING & NORMALIZATION ===")
    
    try:
        from bs4 import BeautifulSoup

        ensure_buckets()

        with ENGINE.connect() as conn:
            # Read recently ingested articles from the warehouse.
            query = """
            SELECT article_id, title, author, content, source, category,
                published_at, url, canonical_url,
                COALESCE(ingested_at, created_at) AS scraped_at
            FROM articles_detail
            WHERE COALESCE(ingested_at, created_at) > NOW() - INTERVAL '1 hour'
            ORDER BY COALESCE(ingested_at, created_at) DESC
            """
            df = pd.read_sql(query, conn)
        
        if df.empty:
            logger.warning("No new articles to transform")
            return 0
        
        logger.info(f"Processing {len(df)} articles for Silver layer")
        
        # Cleaning operations
        def clean_html(html_text):
            """Remove HTML tags and normalize whitespace."""
            if not html_text:
                return ""
            soup = BeautifulSoup(html_text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return re.sub(r'\s+', ' ', text)
        
        def normalize_text(text):
            """Normalize text encoding and punctuation."""
            if not text:
                return ""
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            # Remove special characters but keep accents
            text = re.sub(r'[^\w\s\-àâäæçéèêëîïôœùûüœÿñ.,!?]', '', text)
            return text
        
        # Apply transformations
        df['content_clean'] = df['content'].apply(clean_html)
        df['title_normalized'] = df['title'].apply(normalize_text)
        df['content_length'] = df['content_clean'].str.len()
        df['word_count'] = df['content_clean'].str.split().str.len()
        
        # Language detection (simplified)
        def detect_language(text):
            if not text:
                return 'unknown'
            # Simple heuristic based on keywords
            fr_indicators = ['le', 'la', 'de', 'un', 'une', 'et', 'est']
            en_indicators = ['the', 'a', 'is', 'and', 'to', 'of']
            
            text_lower = text.lower()
            fr_count = sum(1 for word in fr_indicators if word in text_lower)
            en_count = sum(1 for word in en_indicators if word in text_lower)
            
            if fr_count > en_count:
                return 'fr'
            elif en_count > fr_count:
                return 'en'
            else:
                return 'mixed'
        
        df['detected_language'] = df['content_clean'].apply(detect_language)
        
        # Add metadata
        df['silver_timestamp'] = datetime.utcnow().isoformat()
        df['data_quality_score'] = (
            (df['content_length'] > 100).astype(int) +
            (df['word_count'] > 20).astype(int) +
            (df['title'].notna()).astype(int)
        ) / 3
        
        # Save to MinIO Silver
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        silver_file = f"articles_cleaned_{timestamp}.parquet"
        
        from io import BytesIO
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)
        
        MINIO_CLIENT.put_object(
            BUCKET_SILVER,
            silver_file,
            parquet_buffer,
            length=len(parquet_buffer.getvalue()),
            content_type="application/octet-stream"
        )
        logger.info(f"Uploaded {silver_file} to Silver layer ({len(df)} rows)")
        
        # Insert into Silver table in PostgreSQL
        article_ids = df['article_id'].dropna().astype(str).tolist()
        with ENGINE.begin() as conn:
            if article_ids:
                delete_statement = sa.text(
                    "DELETE FROM articles_silver WHERE article_id IN :article_ids"
                ).bindparams(sa.bindparam("article_ids", expanding=True))
                conn.execute(delete_statement, {"article_ids": article_ids})
            df.to_sql('articles_silver', conn, if_exists='append', index=False)
        
        return len(df)
    
    except Exception as e:
        logger.error(f"Silver transformation failed: {e}")
        raise


def load_gold():
    """
    Gold Layer: Create analytical tables
    Aggregate by day, source, theme, and country
    """
    logger.info("=== GOLD LAYER: ANALYTICAL AGGREGATION ===")
    
    try:
        with ENGINE.connect() as conn:
            df = pd.read_sql(
                """
                SELECT title, content, source, category, published_at
                FROM articles_detail
                """,
                conn,
            )

        if df.empty:
            logger.warning("No articles available for gold aggregation")
            return 0

        source_country_map = {entry["name"]: entry.get("country", "Unknown") for entry in load_sources_config()}
        df["source_country"] = df["source"].map(source_country_map).fillna("Unknown")
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
        df["published_day"] = df["published_at"].dt.date
        df["theme"] = (df["title"].fillna("") + " " + df["content"].fillna("")).map(_infer_theme)

        by_day = df.groupby("published_day", dropna=False).size().reset_index(name="articles_count")
        by_source = df.groupby("source", dropna=False).size().reset_index(name="articles_count")
        by_theme = df.groupby("theme", dropna=False).size().reset_index(name="articles_count")
        by_country = df.groupby("source_country", dropna=False).size().reset_index(name="articles_count")
        by_category = df.groupby("category", dropna=False).size().reset_index(name="articles_count")
        top_keywords = _top_keywords(df["title"], top_n=100)

        with ENGINE.begin() as conn:
            for table in [
                "articles_by_day",
                "articles_by_source",
                "articles_by_theme",
                "articles_by_country",
                "articles_by_category",
                "top_keywords",
            ]:
                conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

            conn.execute(sa.text("TRUNCATE TABLE articles_by_day, articles_by_source, articles_by_theme, articles_by_country, articles_by_category, top_keywords"))

            by_day.to_sql("articles_by_day", conn, if_exists="append", index=False)
            logger.info("Updated articles_by_day")

            by_source["last_updated"] = datetime.utcnow()
            by_source.to_sql("articles_by_source", conn, if_exists="append", index=False)
            logger.info("Updated articles_by_source")

            by_theme["last_updated"] = datetime.utcnow()
            by_theme.to_sql("articles_by_theme", conn, if_exists="append", index=False)
            logger.info("Updated articles_by_theme")

            by_country["last_updated"] = datetime.utcnow()
            by_country.to_sql("articles_by_country", conn, if_exists="append", index=False)
            logger.info("Updated articles_by_country")

            by_category["last_updated"] = datetime.utcnow()
            by_category.to_sql("articles_by_category", conn, if_exists="append", index=False)
            logger.info("Updated articles_by_category")

            top_keywords["last_updated"] = datetime.utcnow()
            top_keywords.to_sql("top_keywords", conn, if_exists="append", index=False)
            logger.info("Updated top_keywords")
        
        logger.info("Gold layer aggregations complete")
        return 6  # Number of gold tables updated
    
    except Exception as e:
        logger.error(f"Gold loading failed: {e}")
        raise


def generate_metrics():
    """Generate KPI metrics for dashboards."""
    logger.info("=== GENERATING METRICS ===")
    
    try:
        with ENGINE.connect() as conn:
            metrics = {
                'total_articles': conn.execute(
                    sa.text("SELECT COUNT(*) FROM articles_detail")
                ).scalar(),
                'articles_today': conn.execute(
                    sa.text("SELECT COUNT(*) FROM articles_detail WHERE DATE(published_at) = CURRENT_DATE")
                ).scalar(),
                'quarantined_articles': conn.execute(
                    sa.text("SELECT COUNT(*) FROM articles_detail WHERE quarantine = true")
                ).scalar(),
                'unique_sources': conn.execute(
                    sa.text("SELECT COUNT(DISTINCT source) FROM articles_detail")
                ).scalar(),
            }
        
        logger.info(f"Metrics: {metrics}")
        return metrics
    
    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        return {}
