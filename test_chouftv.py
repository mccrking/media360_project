#!/usr/bin/env python
from src.scraping.scraper import scrape_latest_articles

recs = scrape_latest_articles(20)
chouf = [r for r in recs if r.get("source") == "ChoufTV"]
print(f"Total scraped: {len(recs)}")
print(f"ChoufTV articles: {len(chouf)}")

for c in chouf:
    print(f"  Title: {c.get('title', 'N/A')[:60]}")
    print(f"  URL: {c.get('url', 'N/A')[:80]}")
