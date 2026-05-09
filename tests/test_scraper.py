from bs4 import BeautifulSoup
from src.scraping.scraper import _extract_best_title


def test_extract_best_title_prefers_og_and_cleans():
    html = '<html><head><meta property="og:title" content="Breaking: Something Happened - Site"></head><body><p>content</p></body></html>'
    soup = BeautifulSoup(html, 'html.parser')
    title = _extract_best_title(soup, "Feed Title")
    assert "Breaking: Something Happened" in title
