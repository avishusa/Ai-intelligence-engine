"""
agents/formatter/formatter.py  —  HERALD
Builds the Strategic Weekly Digest and delivers to Discord and Telegram.

Duplicate handling:
  CABAL already deduplicates via seen_article_ids.json — articles
  seen in previous runs are skipped before reaching HERALD.
  HERALD's job is to communicate clearly in ALL cases:
  - New articles exist: send full digest
  - Some competitors have no new articles: call that out per company
  - Zero new articles from anyone: send a clean no-news digest
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

PIPELINE_DIR  = Path("/app/data/pipeline")
ANALYZED_FILE = PIPELINE_DIR / "analyzed_articles.json"
RAW_FILE      = PIPELINE_DIR / "raw_articles.json"
LAST_RUN_FILE = PIPELINE_DIR / "last_delivery.json"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")

THREAT_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
COLOR_MAP    = {"HIGH": 0xFF0000, "MEDIUM": 0xFFAA00, "LOW": 0x00AA44}

# The three competitors we always track — used to detect which
# ones had zero new articles this week
TRACKED_COMPETITORS = ["Union Pacific", "Norfolk Southern", "BNSF Railway"]

def log(msg):
    print(f"[HERALD] {msg}", flush=True)

def load_last_delivery() -> dict:
    if LAST_RUN_FILE.exists():
        return json.loads(LAST_RUN_FILE.read_text())
    return {"date": None, "article_count": 0}

def save_last_delivery(article_count: int):
    LAST_RUN_FILE.write_text(json.dumps({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "article_count": article_count,
        "delivered_at": datetime.now(timezone.utc).isoformat()
    }, indent=2))

def get_competitors_with_no_news(articles: list) -> list:
    """
    WHY per-competitor tracking?
    If BNSF had nothing new but UP and NS did, your Lead needs to
    know that — it might mean BNSF went quiet on tech announcements,
    which is itself a strategic signal worth noting.
    """
    sources_with_news = {a["source"] for a in articles}
    return [c for c in TRACKED_COMPETITORS if c not in sources_with_news]

def send_discord(payload: dict) -> bool:
    if not DISCORD_WEBHOOK_URL:
        log("No Discord webhook configured — skipping.")
        return False
    r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    return r.status_code in (200, 204)

def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("No Telegram credentials — skipping.")
        return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id":   TELEGRAM_CHAT_ID,
            "text":      text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        },
        timeout=10
    )

def build_discord_embed(article: dict) -> dict:
    analysis = article.get("gemini_analysis", {})
    threat   = analysis.get("threat_level", "LOW")
    emoji    = THREAT_EMOJI.get(threat, "⚪")
    color    = COLOR_MAP.get(threat, 0x888888)

    return {
        "title": f"{emoji} {article['source']} — {article['article_title'][:200]}",
        "url":   article["article_url"],
        "color": color,
        "fields": [
            {
                "name":   "📋 Summary",
                "value":  analysis.get("one_line_summary", "N/A")[:1024],
                "inline": False
            },
            {
                "name":   "🎯 CSX Strategic Implication",
                "value":  analysis.get("csx_strategic_implication", "N/A")[:1024],
                "inline": False
            },
            {
                "name":   "⚡ Recommended Action",
                "value":  analysis.get("recommended_action", "N/A")[:1024],
                "inline": False
            },
            {
                "name":   "🛠️ Technologies",
                "value":  ", ".join(analysis.get("key_technologies_mentioned", [])) or "N/A",
                "inline": True
            },
            {
                "name":   "📅 Published",
                "value":  article.get("published_date", "N/A"),
                "inline": True
            },
        ],
        "footer": {
            "text": f"CSX AI Intelligence Engine • {article.get('source_url', '')}"
        }
    }

def build_no_news_footer(silent_competitors: list, last: dict) -> dict:
    """
    Build a clean footer embed that tells your Lead which competitors
    had no new AI/tech activity this week. This runs whether we have
    articles or not — it always closes the digest with a status summary.
    """
    lines = []
    for competitor in TRACKED_COMPETITORS:
        if competitor in silent_competitors:
            lines.append(f"⚫ **{competitor}** — no new AI/tech activity this week")
        else:
            lines.append(f"✅ **{competitor}** — updates delivered above")

    last_date = last.get("date", "first run")
    return {
        "embeds": [{
            "title":       "📊 Weekly Coverage Summary",
            "description": "\n".join(lines),
            "color":       0x444441,
            "footer": {
                "text": f"CSX AI Intelligence Engine • Previous delivery: {last_date} • Next run: Monday 07:00 UTC"
            }
        }]
    }

def deliver_no_news_digest():
    """
    Called when ALL three competitors had zero new articles.
    Sends a professional status message instead of silence.
    """
    week_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    last     = load_last_delivery()

    send_discord({
        "embeds": [{
            "title": "🚂 CSX AI Intelligence Engine — Weekly Check-In",
            "description": (
                f"**Week of {week_str}**\n\n"
                f"No new AI or technology press releases detected this week "
                f"from any tracked competitor.\n\n"
                f"⚫ **Union Pacific** — no new AI/tech activity\n"
                f"⚫ **Norfolk Southern** — no new AI/tech activity\n"
                f"⚫ **BNSF Railway** — no new AI/tech activity\n\n"
                f"All newsrooms were checked. Previously delivered articles "
                f"are excluded to prevent duplicates. System is healthy and "
                f"will run again next Monday at 07:00 UTC."
            ),
            "color": 0x888888,
            "footer": {
                "text": f"CSX AI Intelligence Engine • Previous delivery: {last.get('date', 'first run')}"
            }
        }]
    })

    send_telegram(
        f"🚂 *CSX AI Intel — Week of {week_str}*\n\n"
        f"No new competitor AI/tech activity detected this week.\n\n"
        f"⚫ Union Pacific — no updates\n"
        f"⚫ Norfolk Southern — no updates\n"
        f"⚫ BNSF Railway — no updates\n\n"
        f"System healthy. Next run: Monday 07:00 UTC."
    )
    log("No-news digest delivered.")

def deliver_full_digest(articles: list):
    """
    Delivers the full digest when at least one competitor has new articles.
    Always ends with a coverage summary showing which competitors were silent.
    """
    week_str           = datetime.now(timezone.utc).strftime("%B %d, %Y")
    silent_competitors = get_competitors_with_no_news(articles)
    last               = load_last_delivery()

    # Sort by threat level: HIGH first, then MEDIUM, then LOW
    priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    articles.sort(
        key=lambda a: priority.get(
            a.get("gemini_analysis", {}).get("threat_level", "LOW"), 2
        )
    )

    # Header
    send_discord({
        "content": (
            f"## 🚂 CSX AI Intelligence Engine — Strategic Weekly Digest\n"
            f"**Week of {week_str}** | {len(articles)} new intelligence items\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    })

    # One embed per article
    for article in articles:
        send_discord({"embeds": [build_discord_embed(article)]})

    # Always end with a coverage summary — tells Lead which competitors
    # were checked and which had nothing new this week
    send_discord(build_no_news_footer(silent_competitors, last))

    log(f"Sent {len(articles)} articles to Discord.")

    # Telegram: combined message
    lines = [f"🚂 *CSX AI Intel Digest — {week_str}*\n"]
    for article in articles:
        analysis = article.get("gemini_analysis", {})
        emoji    = THREAT_EMOJI.get(analysis.get("threat_level", "LOW"), "⚪")
        lines.append(
            f"{emoji} *{article['source']}*\n"
            f"_{article['article_title'][:120]}_\n"
            f"{analysis.get('one_line_summary', '')[:200]}\n"
            f"[Read more]({article['article_url']})\n"
        )

    # Add silent competitor note to Telegram too
    if silent_competitors:
        lines.append(
            f"\n📊 *No new activity this week from:*\n" +
            "\n".join(f"⚫ {c}" for c in silent_competitors)
        )

    send_telegram("\n".join(lines))
    log("Sent digest to Telegram.")

def format_and_deliver():
    print("=" * 60, flush=True)
    log("Building Strategic Weekly Digest...")
    print("=" * 60, flush=True)

    # No analyzed file at all — something went wrong upstream
    if not ANALYZED_FILE.exists():
        log("No analyzed_articles.json found — delivering no-news digest.")
        deliver_no_news_digest()
        save_last_delivery(0)
        return

    articles = json.loads(ANALYZED_FILE.read_text())

    # Empty file — CABAL found nothing new after deduplication
    if not articles:
        log("Zero new articles after deduplication — delivering no-news digest.")
        deliver_no_news_digest()
        save_last_delivery(0)
        return

    # We have real new articles — deliver the full digest
    deliver_full_digest(articles)
    save_last_delivery(len(articles))
    log("Digest delivery complete.")

if __name__ == "__main__":
    format_and_deliver()
