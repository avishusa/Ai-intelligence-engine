"""
agents/formatter/formatter.py  —  HERALD
WHY THIS FILE:
  HERALD reads fully-analyzed articles and assembles them into
  a professional "Strategic Weekly Digest" then fires it to
  Discord via webhook — zero manual steps required.
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime

PIPELINE_DIR  = Path("/app/data/pipeline")
ANALYZED_FILE = PIPELINE_DIR / "analyzed_articles.json"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")

# Threat level → emoji mapping for visual scanning in Discord
THREAT_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

def build_discord_embed(article: dict) -> dict:
    """
    WHY Discord embeds?
    Plain text messages in Discord are unreadable walls of text.
    Embeds = structured cards with color-coded threat levels.
    Your Lead will see this at a glance on mobile.
    """
    analysis = article.get("gemini_analysis", {})
    threat   = analysis.get("threat_level", "LOW")
    emoji    = THREAT_EMOJI.get(threat, "⚪")

    # Embed color: Red=HIGH, Yellow=MEDIUM, Green=LOW
    color_map = {"HIGH": 0xFF0000, "MEDIUM": 0xFFAA00, "LOW": 0x00AA44}
    color = color_map.get(threat, 0x888888)

    return {
        "title": f"{emoji} {article['source']} — {article['article_title'][:200]}",
        "url":   article["article_url"],
        "color": color,
        "fields": [
            {
                "name": "📋 Summary",
                "value": analysis.get("one_line_summary", "N/A"),
                "inline": False
            },
            {
                "name": "🎯 Strategic Implication",
                "value": analysis.get("Strategic_implication", "N/A"),
                "inline": False
            },
            {
                "name": "⚡ Recommended Action",
                "value": analysis.get("recommended_action", "N/A"),
                "inline": False
            },
            {
                "name": "🛠️ Technologies",
                "value": ", ".join(analysis.get("key_technologies_mentioned", [])) or "N/A",
                "inline": True
            },
            {
                "name": "📅 Published",
                "value": article.get("published_date", "N/A"),
                "inline": True
            },
        ],
        "footer": {
            "text": f"AI Intelligence Engine • Source: {article.get('source_url', '')}"
        }
    }

def send_to_discord(articles: list):
    if not DISCORD_WEBHOOK_URL:
        print("[HERALD] No Discord webhook configured — skipping.")
        return

    # Send a header message first
    week_str = datetime.now().strftime("%B %d, %Y")
    header_payload = {
        "content": (
            f"## 🚂 AI Intelligence Engine — Strategic Weekly Digest\n"
            f"**Week of {week_str}** | {len(articles)} competitor intelligence items\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    }
    requests.post(DISCORD_WEBHOOK_URL, json=header_payload, timeout=10)

    # Send each article as its own embed
    for article in articles:
        embed = build_discord_embed(article)
        payload = {"embeds": [embed]}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code not in (200, 204):
            print(f"[HERALD] Discord error {response.status_code}: {response.text}")

    print(f"[HERALD] ✓ Sent {len(articles)} articles to Discord.")

def send_to_telegram(articles: list):
    """Optional Telegram delivery — sends a plain-text digest."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[HERALD] No Telegram credentials — skipping.")
        return

    week_str = datetime.now().strftime("%B %d, %Y")
    lines = [f"🚂 *AI Intel Digest — {week_str}*\n"]

    for article in articles:
        analysis = article.get("gemini_analysis", {})
        threat   = article.get("threat_level", "LOW")
        emoji    = THREAT_EMOJI.get(analysis.get("threat_level", "LOW"), "⚪")
        lines.append(
            f"{emoji} *{article['source']}*\n"
            f"_{article['article_title']}_\n"
            f"{analysis.get('one_line_summary', '')}\n"
            f"[Read more]({article['article_url']})\n"
        )

    message = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }, timeout=10)
    print(f"[HERALD] ✓ Sent digest to Telegram.")

def format_and_deliver():
    print("=" * 60)
    print("[HERALD] Building Strategic Weekly Digest...")
    print("=" * 60)

    if not ANALYZED_FILE.exists():
        print("[HERALD] No analyzed_articles.json found. Run DAEDALUS first.")
        return

    articles = json.loads(ANALYZED_FILE.read_text())
    if not articles:
        print("[HERALD] No articles to deliver — sending 'no new intel' ping.")
        if DISCORD_WEBHOOK_URL:
            requests.post(DISCORD_WEBHOOK_URL, json={
                "content": "🚂 AI Intel Engine: No new competitor AI/tech activity this week."
            }, timeout=10)
        return

    # Sort by threat level: HIGH first
    priority = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    articles.sort(
        key=lambda a: priority.get(
            a.get("gemini_analysis", {}).get("threat_level", "LOW"), 2
        )
    )

    send_to_discord(articles)
    send_to_telegram(articles)
    print("\n[HERALD] Digest delivery complete.")

if __name__ == "__main__":
    format_and_deliver()