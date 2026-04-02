"""
agents/orchestrator/orchestrator.py  —  CABAL
Reads scraper output (stdout=JSON, stderr=logs) and orchestrates the pipeline.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

PIPELINE_DIR = Path("/app/data/pipeline")
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILE    = PIPELINE_DIR / "raw_articles.json"
SCORED_FILE = PIPELINE_DIR / "scored_articles.json"
SEEN_FILE   = PIPELINE_DIR / "seen_article_ids.json"

HIGH_VALUE_KEYWORDS = [
    "artificial intelligence", "machine learning", "AI", "autonomous",
    "automation", "predictive maintenance", "digital twin", "algorithm",
    "computer vision", "robotics", "data analytics", "sensor fusion",
    "locomotive technology", "Wabtec", "software platform"
]

MEDIUM_VALUE_KEYWORDS = [
    "technology", "digital", "innovation", "data", "efficiency",
    "intermodal", "modernization", "platform", "smart", "connected"
]

def log(msg):
    print(f"[CABAL] {msg}", flush=True)

def load_seen_ids():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()

def save_seen_ids(seen_ids):
    SEEN_FILE.write_text(json.dumps(list(seen_ids), indent=2))

def score_article(title: str) -> int:
    title_lower = title.lower()
    if any(kw.lower() in title_lower for kw in HIGH_VALUE_KEYWORDS):
        return 5
    if any(kw.lower() in title_lower for kw in MEDIUM_VALUE_KEYWORDS):
        return 3
    return 1

def run_scrapers():
    scrapers = [
        ("UP Scout",     "/app/agents/scraper-up/scraper.py"),
        ("NS Sentinel",  "/app/agents/scraper-ns/scraper.py"),
        ("BNSF Watcher", "/app/agents/scraper-bnsf/scraper.py"),
    ]

    all_articles = []
    for name, script_path in scrapers:
        log(f"Triggering {name}...")
        try:
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True,   # stdout=JSON, stderr=logs
                text=True,
                timeout=60
            )

            # WHY print stderr separately?
            # Scraper logs go to stderr. We forward them so they appear
            # in docker logs for debugging, but don't mix with JSON stdout.
            if result.stderr:
                print(result.stderr, end="", flush=True)

            stdout = result.stdout.strip()
            if not stdout:
                log(f"{name} returned empty output — skipping.")
                continue

            if result.returncode == 0:
                articles = json.loads(stdout)
                all_articles.extend(articles)
                log(f"{name} returned {len(articles)} articles.")
            else:
                log(f"{name} FAILED (exit {result.returncode}): {result.stderr}")

        except subprocess.TimeoutExpired:
            log(f"{name} timed out — skipping.")
        except json.JSONDecodeError as e:
            log(f"{name} returned invalid JSON: {e}")
            log(f"Raw stdout was: {repr(result.stdout[:200])}")

    RAW_FILE.write_text(json.dumps(all_articles, indent=2))
    log(f"Saved {len(all_articles)} raw articles → {RAW_FILE}")
    return all_articles

def orchestrate():
    print("=" * 60, flush=True)
    log("Starting orchestration run...")
    print("=" * 60, flush=True)

    all_articles = run_scrapers()
    seen_ids     = load_seen_ids()
    scored       = []
    new_seen_ids = set()

    for article in all_articles:
        article_id = article.get("article_id", "")

        if article_id in seen_ids:
            log(f"SKIP (already seen): {article['article_title'][:60]}")
            continue

        score = score_article(article["article_title"])
        article["relevance_score"] = score

        if score >= 3:
            scored.append(article)
            new_seen_ids.add(article_id)
            log(f"PASS (score={score}): {article['article_title'][:60]}")
        else:
            log(f"DROP (score={score}): {article['article_title'][:60]}")

    SCORED_FILE.write_text(json.dumps(scored, indent=2))
    save_seen_ids(seen_ids | new_seen_ids)
    log(f"Done. {len(scored)} articles passed to DAEDALUS → {SCORED_FILE}")
    return scored

if __name__ == "__main__":
    orchestrate()
