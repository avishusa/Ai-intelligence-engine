"""
agents/scraper-bnsf/scraper.py
Uses Crawl4AI to scrape BNSF Railway news from Progressive Railroading.

WHY Progressive Railroading instead of bnsf.com directly?

bnsf.com/news-media/news-releases/library.page — JavaScript-rendered
VIEW buttons, relId links never appear in Crawl4AI result.links.

businesswire.com search — also JavaScript-rendered, returns 1 link total.

Progressive Railroading (progressiverailroading.com/bnsf_railway/) is:
- A respected, 60-year-old trade publication for rail industry professionals
- Static HTML — all links fully visible to Crawl4AI
- Has a dedicated BNSF section updated with every major announcement
- Covers BNSF technology, innovation, operations, and capital news
- Authentic: content sourced directly from BNSF press releases and interviews
- Your CSX Lead will recognize and trust this source immediately

This is the same publication that railway executives, investors, and
regulators read. Enterprise-grade intelligence comes from trade press,
not just corporate newsrooms.
"""

import sys
import json
import hashlib
import asyncio
import re
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

SOURCE_NAME = "BNSF Railway"
SOURCE_URL  = "https://www.progressiverailroading.com/bnsf_railway/"

AI_TECH_KEYWORDS = [
    "artificial intelligence", " ai ", "machine learning", "automation",
    "technology", "digital", "data", "predictive", "autonomous",
    "innovation", "analytics", "wabtec", "locomotive", "sensor",
    "safety technology", "efficiency", "software", "barstow",
    "logistics", "moderniz", "capital", "intermodal",
    "network", "operations", "platform", "physics train",
    "quantum", "tool", "system", "upgrade", "investment"
]

def log(msg):
    print(f"[BNSF Watcher] {msg}", file=sys.stderr, flush=True)

def clean_title(title: str) -> str:
    """Strip date prefixes and collapse whitespace."""
    # Remove patterns like 'February 26, 2026\n' at the start
    title = re.sub(r'^[A-Z][a-z]+ \d{1,2}, \d{4}\s*', '', title)
    # Collapse all whitespace including newlines into single space
    title = re.sub(r'\s+', ' ', title).strip()
    # Remove trailing ' »' which Progressive Railroading appends to links
    title = title.rstrip(' »').strip()
    return title

def is_relevant(title: str) -> bool:
    return any(kw in title.lower() for kw in AI_TECH_KEYWORDS)

async def fetch_articles():
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        browser_type="chromium"
    )

    # WHY domcontentloaded?
    # Progressive Railroading is a traditional static HTML site.
    # domcontentloaded is sufficient and fast — no JS rendering needed.
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

    articles  = []
    seen_ids  = set()

    all_links = result.links.get("internal", []) + result.links.get("external", [])
    log(f"Found {len(all_links)} total links to filter")

    for link in all_links:
        href      = link.get("href", "")
        raw_title = link.get("text", "").strip()
        title     = clean_title(raw_title)

        # Progressive Railroading article URLs contain /news/ or /article/
        # or /bnsf_railway/news/ — filter for actual content pages
        is_article = (
            "/bnsf_railway/news/" in href or
            "/bnsf_railway/article/" in href or
            "/RailPrime/details/" in href
        )
        if not is_article:
            continue

        # Skip very short titles — section headers, nav labels
        if len(title) < 25:
            continue

        if not is_relevant(title):
            continue

        url        = href if href.startswith("http") else "https://www.progressiverailroading.com" + href
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
