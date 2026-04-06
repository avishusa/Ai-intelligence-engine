"""
agents/orchestrator/orchestrator.py  —  CABAL
Orchestrates the full pipeline: triggers scrapers, deduplicates,
scores relevance, and writes scored_articles.json for DAEDALUS.
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

PIPELINE_DIR = Path("/app/data/pipeline")
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILE    = PIPELINE_DIR / "raw_articles.json"
SCORED_FILE = PIPELINE_DIR / "scored_articles.json"
SEEN_FILE   = PIPELINE_DIR / "seen_article_ids.json"

# Score 5 = highly strategic AI/tech signal for CSX AI Lead
HIGH_VALUE_KEYWORDS = [
    "artificial intelligence", "machine learning", " ai ",
    "autonomous", "automation", "predictive maintenance",
    "digital twin", "algorithm", "computer vision", "robotics",
    "data analytics", "sensor fusion", "locomotive technology",
    "wabtec", "software platform", "moderniz", "east edge",
    "double-stack", "intermodal technology", "precision scheduled",
    "real-time", "optimization", "physics train", "quantum intermodal",
    "technology investment", "tech", "digital transformation",
    "innovation invest", "capital invest"
]

# Score 3 = relevant context, worth monitoring
MEDIUM_VALUE_KEYWORDS = [
    "intermodal", "platform", "smart", "connected",
    "efficiency", "network upgrade", "logistics center",
    "infrastructure invest", "expansion project"
]

# These words cause false positives — articles containing ONLY these
# without any HIGH/MEDIUM keyword get dropped
NOISE_PHRASES = [
    "donation", "charity", "scholarship", "community grant",
    "labor agreement", "union contract", "dividend", "earnings call",
    "board of directors", "executive appoint", "retirement",
    "heritage", "anniversary", "steam locomotive tour"
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
    """
    Score an article 1-5 for AI/tech relevance to CSX.

    WHY noise filtering?
    Broad keywords like 'million' or 'network' can match donation
    announcements, labor agreements, or earnings calls — none of
    which are relevant to a Lead of AI Delivery. We explicitly
    drop articles whose titles contain only noise phrases with no
    compensating high-value signal.
    """
    t = title.lower()

    # First check: is this a noise article?
    # If any noise phrase matches AND no high-value keyword matches,
    # immediately drop it regardless of medium keyword matches.
    has_noise     = any(phrase in t for phrase in NOISE_PHRASES)
    has_high      = any(kw in t for kw in HIGH_VALUE_KEYWORDS)
    has_medium    = any(kw in t for kw in MEDIUM_VALUE_KEYWORDS)

    if has_noise and not has_high:
        return 1   # Drop — noise article with no tech signal

    if has_high:
        return 5   # Strong AI/tech signal

    if has_medium:
        return 3   # Relevant context

    return 1       # Not relevant

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
                capture_output=True,
                text=True,
                timeout=120
            )

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
                log(f"{name} FAILED (exit {result.returncode})")

        except subprocess.TimeoutExpired:
            log(f"{name} timed out after 120s — skipping.")
        except json.JSONDecodeError as e:
            log(f"{name} returned invalid JSON: {e}")
            log(f"Raw stdout: {repr(result.stdout[:300])}")

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
            log(f"PASS (score={score}): {article['article_title'][:70]}")
        else:
            log(f"DROP (score={score}): {article['article_title'][:70]}")

    SCORED_FILE.write_text(json.dumps(scored, indent=2))
    save_seen_ids(seen_ids | new_seen_ids)
    log(f"Done. {len(scored)} articles passed to DAEDALUS → {SCORED_FILE}")
    return scored

if __name__ == "__main__":
    orchestrate()
