from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from src.common import load_sources_config, now_utc_iso

USER_AGENT = "Mozilla/5.0 (compatible; DataArchitectureProject/1.0)"
TIMEOUT_SECONDS = 15


def _to_iso_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return date_parser.parse(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def _extract_article_content(url: str) -> tuple[BeautifulSoup, str, str, str]:
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except Exception:
        return BeautifulSoup("", "html.parser"), "", "", ""

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p) > 30]
    text = "\n".join(paragraphs[:30])
    html = "\n".join(str(p) for p in soup.find_all("p")[:30])
    # try to find canonical URL
    canonical = ""
    link_canon = soup.find("link", rel="canonical")
    if link_canon and link_canon.get("href"):
        canonical = link_canon.get("href")
    og_url = soup.find("meta", property="og:url") or soup.find("meta", attrs={"name": "og:url"})
    if og_url and og_url.get("content"):
        canonical = og_url.get("content")

    return soup, html, text, canonical


def _extract_best_title(soup: BeautifulSoup, feed_title: str | None) -> str:
    """Try several strategies to get a clean article title.

    Priority:
    1. meta property og:title
    2. <title> tag
    3. feed_title (if present and not generic)
    4. fallback to feed_title or empty string
    After extraction, apply simple cleaning heuristics.
    """
    def clean_candidate(t: str) -> str:
        if not t:
            return ""
        t = re.sub(r"\s+", " ", t).strip()
        # remove site suffixes like " - BBC News" or " | Reuters"
        t = re.sub(r"\s[-|—|\|]\s.*$", "", t)
        return t

    blacklist = {"register", "sign in", "signin", "home", "news", "sport", "live", "watch", "listen"}

    candidates: list[str] = []

    # og:title (preferred)
    og = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "og:title"})
    if og and og.get("content"):
        candidates.append(og.get("content"))

    # meta title
    meta_title = soup.find("title")
    if meta_title:
        candidates.append(meta_title.get_text())

    # feed title as fallback
    if feed_title:
        candidates.append(feed_title)

    for cand in candidates:
        t = clean_candidate(cand)
        low = t.lower()
        # filter out short or nav-like titles
        if len(t) < 8:
            continue
        if low in blacklist:
            continue
        # discard titles that look like menus (single word common labels)
        if len(t.split()) <= 2 and any(word in low for word in blacklist):
            continue
        # must contain at least one letter
        if not re.search(r"[a-zA-ZÀ-ÿ]", t):
            continue
        return t

    # fallback: return cleaned feed_title or empty
    return clean_candidate(feed_title or "")


def _extract_category(entry: Any) -> str:
    if getattr(entry, "tags", None):
        tag = entry.tags[0]
        if isinstance(tag, dict):
            return str(tag.get("term", "Unknown"))
        return str(getattr(tag, "term", "Unknown"))
    return "Unknown"


def scrape_latest_articles(limit_per_source: int = 20) -> list[dict[str, Any]]:
    all_articles: list[dict[str, Any]] = []
    sources = load_sources_config()

    for source in sources:
        feed = feedparser.parse(source["rss_url"])
        entries = feed.entries[:limit_per_source]

        for entry in entries:
            url = entry.get("link", "")
            if not url:
                continue
            soup, html_content, text_content, canonical_url = _extract_article_content(url)
            feed_title = entry.get("title", "")
            title = _extract_best_title(soup, feed_title)

            # skip if no valid title extracted
            if not title:
                continue
            # Keep the source/feed URL for display; use canonical only for stable identity.
            stable_url = canonical_url or url
            article_id = hashlib.sha256(stable_url.encode("utf-8")).hexdigest()[:24]
            article = {
                "article_id": article_id,
                "title": title,
                "author": entry.get("author", "Unknown"),
                "published_at": _to_iso_date(entry.get("published") or entry.get("updated")),
                "category": _extract_category(entry),
                "content_html": html_content,
                "content": text_content,
                "source": source["name"],
                "source_country": source["country"],
                "url": url,
                "canonical_url": canonical_url,
                "scraped_at": now_utc_iso(),
            }
            all_articles.append(article)

    # deduplicate by article_id preserving order
    seen: set[str] = set()
    unique_articles: list[dict[str, Any]] = []
    for a in all_articles:
        aid = a.get("article_id")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        unique_articles.append(a)

    return unique_articles


if __name__ == "__main__":
    records = scrape_latest_articles()
    print(f"Scraped {len(records)} articles")
