"""
agents/scraper-up/scraper.py
Uses Crawl4AI with headless Chromium to scrape Union Pacific's official newsroom.

WHY Crawl4AI instead of BeautifulSoup?
  UP's newsroom loads articles via JavaScript after page load.
  BeautifulSoup only reads the initial HTML — it never sees the articles.
  Crawl4AI launches a real browser, waits for JS to execute, then
  returns clean markdown we can reliably parse.

Source: https://www.up.com/press-releases (official UP corporate newsroom)
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
    "sensor", "computer vision", "innovation", "moderniz", "efficiency"
]

def log(msg):
    print(f"[UP Scout] {msg}", file=sys.stderr, flush=True)

def is_relevant(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in AI_TECH_KEYWORDS)

async def fetch_articles():
    # WHY BrowserConfig headless=True?
    # We don't need a visible browser window inside Docker.
    # Headless mode runs the full browser engine without rendering UI —
    # faster and uses less memory.
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,          # Set True if you want browser debug logs
        browser_type="chromium"
    )

    # WHY CacheMode.BYPASS?
    # We always want fresh data — never return a cached page from last week.
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=5,     # Ignore tiny text blocks (nav labels)
        remove_overlay_elements=True,  # Remove cookie popups and modals
        wait_until="networkidle",   # Wait for JS to finish loading
        page_timeout=30000          # 30 second timeout
    )

    log(f"Launching headless browser for {SOURCE_URL}")

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=SOURCE_URL, config=run_config)

    if not result.success:
        log(f"ERROR: Crawl failed — {result.error_message}")
        return []

    # Crawl4AI returns result.links — a dict with 'internal' and 'external' lists
    # Each li # Each link has 'href' and 'text' keys
    articles = []
    seen_ids = set()

    internal_links = result.links.get("internal", [])
    log(f"Found {len(internal_links)} internal links to filter")

    for link in internal_links:
        href  = link.get("href", "")
        title = link.get("text", "").strip()

        # WHY these filters?
        # press-releases/ in the URL = it's an actual press release page
        # len > 20 = real titles, not nav labels like "Home" or "Contact"
        if "press-releases" not in href and "news" not in href:
            continue
        if len(title) < 25:
            continue
        if not is_relevant(title):
            continue

        url = href if href.startswith("http") else "https://www.up.com" + href
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
    # ONLY JSON to stdout — logs go to stderr
    print(json.dumps(results))

if __name__ == "__main__":
    main()
