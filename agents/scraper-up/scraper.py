"""
agents/scraper-up/scraper.py
Uses Crawl4AI with headless Chromium to scrape Union Pacific's official newsroom.
Source: https://www.up.com/press-releases
"""

import sys
import json
import hashlib
import asyncio
import re
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

SOURCE_NAME = "Union Pacific"
SOURCE_URL  = "https://www.up.com/press-releases"

AI_TECH_KEYWORDS = [
    "artificial intelligence", " ai ", "machine learning", "automation",
    "technology", "digital", "data analytics", "predictive", "autonomous",
    "robotics", "algorithm", "software", "wabtec", "locomotive moderniz",
    "sensor", "computer vision", "innovation", "moderniz", "efficiency",
    "intermodal", "network", "operations"
]

def log(msg):
    print(f"[UP Scout] {msg}", file=sys.stderr, flush=True)

def clean_title(title: str) -> str:
    title = re.sub(r'^[A-Z][a-z]+ \d{1,2}, \d{4}\s*', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def is_relevant(title: str) -> bool:
    return any(kw in title.lower() for kw in AI_TECH_KEYWORDS)

async def fetch_articles():
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        browser_type="chromium"
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=5,
        remove_overlay_elements=True,
        wait_until="domcontentloaded",
        page_timeout=45000
    )

    log(f"Launching headless browser for {SOURCE_URL}")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=SOURCE_URL, config=run_config)

    if not result.success:
        log(f"ERROR: Crawl failed — {result.error_message}")
        return []

    articles = []
    seen_ids = set()
    internal_links = result.links.get("internal", [])
    log(f"Found {len(internal_links)} internal links to filter")

    for link in internal_links:
        href  = link.get("href", "")
        title = clean_title(link.get("text", "").strip())

        if "press-releases" not in href and "news" not in href:
            continue
        if len(title) < 20:
            continue
        if not is_relevant(title):
            continue

        url        = href if href.startswith("http") else "https://www.up.com" + href
        article_id = hashlib.md5(url.encode()).hexdigest()

        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)

        articles.append({
            "source":         SOURCE_NAME,
            "source_url":     SOURCE_URL,
            "article_title":  title,
            "article_url":    url,
            "published_date": datetime.now().strftime("%Y-%m-%d"),
            "article_id":     article_id
        })

    log(f"Found {len(articles)} relevant articles.")
    return articles[:10]

def main():
    results = asyncio.run(fetch_articles())
    print(json.dumps(results))

if __name__ == "__main__":
    main()
