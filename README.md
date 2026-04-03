# AI Intelligence Engine

An enterprise-grade multi-agent pipeline that tracks competitor AI and
technology activity across Union Pacific, Norfolk Southern, and BNSF Railway,
delivering a **Strategic Weekly Digest** to Discord/Telegram every Monday at 7AM UTC.

Built for the Lead of AI Delivery at Transportation Company.

## Architecture

\\\
Official Newsrooms (UP / NS / BNSF)
           |
    Crawl4AI headless Chromium
    (handles JavaScript-rendered pages)
           |
    CABAL — orchestrator.py
    (deduplicates, scores 1-5, filters)
           |
    DAEDALUS — analyst.py
    (Gemini 2.5 Flash-Lite, free tier)
           |
    HERALD — formatter.py
    (Discord embeds + Telegram message)
           |
  Your Discord / Telegram channel
\\\

## Agents

| Agent | File | Role |
|-------|------|------|
| UP Scout | scraper-up/scraper.py | Scrapes Union Pacific newsroom |
| NS Sentinel | scraper-ns/scraper.py | Scrapes Norfolk Southern newsroom |
| BNSF Watcher | scraper-bnsf/scraper.py | Scrapes BNSF Railway newsroom |
| CABAL | orchestrator/orchestrator.py | Orchestrates, deduplicates, scores |
| DAEDALUS | analyst/analyst.py | Gemini-powered strategic analysis |
| HERALD | formatter/formatter.py | Formats and delivers digest |

## Tech Stack

- **Scraping**: Crawl4AI + Playwright Chromium (zero JS rendering issues)
- **Orchestration**: Python APScheduler + file-based multi-agent handoff
- **LLM**: Google Gemini 2.5 Flash-Lite (free tier, 1000 req/day)
- **Delivery**: Discord webhook + Telegram bot
- **Security**: Docker sandbox — containers have zero access to host filesystem
- **Version Control**: Git with Conventional Commits

## Security Model

All agents run inside Docker with:
- Named volumes only (no host filesystem mounts)
- Read-only source code mounts
- API keys injected via .env (never committed to Git)
- No ports exposed to host network

## Setup

See docs/SETUP.md for full installation instructions.

## Schedule

Pipeline runs automatically every Monday at 07:00 UTC via APScheduler.
On container startup, one immediate smoke test run is triggered automatically.
