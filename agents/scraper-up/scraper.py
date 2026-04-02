"""
agents/scraper-up/scraper.py
WHY THIS FILE EXISTS: OpenClaw agents can run Python skills.
This script fetches Union Pacific's official newsroom and extracts
press release titles, URLs, and dates. It uses only the official UP domain.
"""

import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- Configuration ---
UP_NEWSROOM_URL = "https://www.up.com/news"
AI_TECH_KEYWORDS = [
    "artificial intelligence", "AI", "machine learning", "automation",
    "technology", "digital", "data analytics", "predictive", "autonomous",
    "robotics", "algorithm", "software", "innovation", "Wabtec",
    "locomotive", "sensor", "computer vision"
]

def fetch_articles():
    """
    WHY requests + BeautifulSoup?
    requests = the standard Python library for making HTTP calls.
    BeautifulSoup = parses HTML into a tree you can search — like a map of the page.
    """
    headers = {
        # WHY a User-Agent? Some sites block requests with no browser identity.
        # We identify ourselves as a research tool — honest and professional.
        "User-Agent": "CSX-AIIntelligenceEngine/1.0 (research; contact: your@email.com)"
    }

    try:
        response = requests.get(UP_NEWSROOM_URL, headers=headers, timeout=15)
        response.raise_for_status()   # Raises an error for 4xx/5xx responses
    except requests.RequestException as e:
        print(f"[UP Scout] ERROR: Could not fetch newsroom — {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # Find article elements — inspect up.com/news to confirm CSS selectors
    articles = []
    # UP newsroom uses <article> tags with headline links inside
    for item in soup.select("article")[:20]:  # Limit to latest 20
        title_tag = item.select_one("h2, h3, .headline")
        link_tag = item.select_one("a[href]")
        date_tag = item.select_one("time, .date")

        if not title_tag or not link_tag:
            continue

        title = title_tag.get_text(strip=True)
        url = link_tag["href"]
        if not url.startswith("http"):
            url = "https://www.up.com" + url
        date = date_tag.get_text(strip=True) if date_tag else datetime.now().strftime("%Y-%m-%d")

        # WHY keyword filtering HERE (not in the orchestrator)?
        # Reduces noise before it ever leaves this agent. Efficient pipeline.
        if any(kw.lower() in title.lower() for kw in AI_TECH_KEYWORDS):
            articles.append({
                "source": "Union Pacific",
                "source_url": UP_NEWSROOM_URL,
                "article_title": title,
                "article_url": url,
                "published_date": date,
                "article_id": hashlib.md5(url.encode()).hexdigest()  # Dedup key
            })

    print(f"[UP Scout] Found {len(articles)} relevant articles.")
    return articles


if __name__ == "__main__":
    results = fetch_articles()
    # Output as JSON for the OpenClaw pipeline to consume
    print(json.dumps(results, indent=2))