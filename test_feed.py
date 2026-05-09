#!/usr/bin/env python
import feedparser

feed = feedparser.parse("https://www.france24.com/fr/rss")
print(f"Entries count: {len(feed.entries)}")
print(f"Feed has title: {bool(feed.get('title'))}")
print(f"Feed title: {feed.get('title', 'N/A')}")

if feed.entries:
    entry = feed.entries[0]
    print(f"\nFirst entry:")
    print(f"  Title: {entry.get('title', 'N/A')}")
    print(f"  Link: {entry.get('link', 'N/A')}")
else:
    print("\nNo entries found in feed")
    print(f"Feed version: {feed.get('version', 'N/A')}")
