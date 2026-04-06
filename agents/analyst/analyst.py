"""
agents/analyst/analyst.py  —  DAEDALUS
WHY THIS FILE:
  Raw article titles tell us WHAT happened.
  DAEDALUS asks Gemini to tell us WHY it matters for our AI strategy.
  This is the intelligence layer — turning news into strategy.

MODEL: gemini-2.5-flash-lite (free tier, 1000 req/day as of March 2026)
WHY FLASH-LITE? Our weekly digest needs at most ~15 API calls per run.
  Flash-Lite gives 1000/day free — massively more than we need.
  It's optimized for exactly this: summarization and classification.
"""

import os
import json
import time
import requests
from pathlib import Path

PIPELINE_DIR  = Path("/app/data/pipeline")
SCORED_FILE   = PIPELINE_DIR / "scored_articles.json"
ANALYZED_FILE = PIPELINE_DIR / "analyzed_articles.json"

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
# WHY this URL format? Google's official REST endpoint for generateContent.
# No SDK dependency — pure HTTP. Simpler to debug inside Docker.
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-lite:generateContent"
    f"?key={GEMINI_API_KEY}"
)

def build_prompt(article: dict) -> str:
    """
    WHY a structured prompt?
    Gemini returns better, more consistent analysis when the prompt
    specifies the exact output format. JSON output = no parsing guesswork.
    """
    return f"""You are a strategic intelligence analyst for Transportation's AI Delivery team.
Analyze this competitor press release and return ONLY valid JSON — no markdown, no explanation.

Competitor: {article['source']}
Article Title: {article['article_title']}
Article URL: {article['article_url']}
Published: {article['published_date']}
Initial Relevance Score: {article['relevance_score']}/5

Return this exact JSON structure:
{{
  "one_line_summary": "One sentence: what happened and why it matters for railroad AI.",
  "Strategic_implication": "2-3 sentences: how this affects competitive position or AI roadmap.",
  "threat_level": "LOW | MEDIUM | HIGH",
  "recommended_action": "One actionable recommendation for AI Lead.",
  "key_technologies_mentioned": ["list", "of", "tech", "terms"]
}}"""

def call_gemini_with_retry(prompt: str, max_retries: int = 5) -> dict | None:
    """
    WHY retry with backoff?
    Free tier rate limits (15 RPM) mean occasionally we'll hit a 429 error.
    Exponential backoff = wait longer each retry. Professional pattern.
    """
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,   # Low temp = consistent, factual output
            "maxOutputTokens": 512
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                GEMINI_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 429:
                wait = 2 ** attempt * 10  # 5s, 10s, 20s
                print(f"[DAEDALUS] Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            response.raise_for_status()
            data = response.json()

            # Extract the text content from Gemini's response structure
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

            # WHY strip()? Gemini sometimes adds whitespace or ```json fences.
            raw_text = raw_text.strip().lstrip("```json").rstrip("```").strip()
            return json.loads(raw_text)

        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            print(f"[DAEDALUS] Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)

    return None

def analyze():
    print("=" * 60)
    print("[DAEDALUS] Starting Gemini analysis run...")
    print("=" * 60)

    if not SCORED_FILE.exists():
        print("[DAEDALUS] No scored_articles.json found. Run CABAL first.")
        return []

    articles = json.loads(SCORED_FILE.read_text())
    if not articles:
        print("[DAEDALUS] No articles to analyze.")
        return []

    analyzed = []
    for i, article in enumerate(articles):
        print(f"\n[DAEDALUS] Analyzing {i+1}/{len(articles)}: {article['article_title'][:60]}")

        prompt = build_prompt(article)
        analysis = call_gemini_with_retry(prompt)

        if analysis:
            article["gemini_analysis"] = analysis
            analyzed.append(article)
            print(f"[DAEDALUS] ✓ Threat level: {analysis.get('threat_level', 'N/A')}")
        else:
            print(f"[DAEDALUS] ✗ Analysis failed — skipping this article.")

        # WHY sleep? Respect free tier rate limits. 15 RPM = 4s between calls is safe.
        time.sleep(8)

    ANALYZED_FILE.write_text(json.dumps(analyzed, indent=2))
    print(f"\n[DAEDALUS] Done. {len(analyzed)} articles analyzed → {ANALYZED_FILE}")
    return analyzed

if __name__ == "__main__":
    analyze()