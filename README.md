# CSX AI Intelligence Engine

A multi-agent pipeline that tracks competitor AI activity across
Union Pacific, Norfolk Southern, and BNSF Railway, delivering a
**Strategic Weekly Digest** to Discord/Telegram every Monday.

## Architecture
- **Scraping**: Crawl4AI with headless Chromium (handles JS-rendered newsrooms)
- **Orchestration**: Python APScheduler + subprocess-based multi-agent pipeline
- **Agents**: UP Scout, NS Sentinel, BNSF Watcher (scrapers) → CABAL (orchestrator) → DAEDALUS (Gemini analyst) → HERALD (formatter)
- **LLM**: Google Gemini 2.5 Flash-Lite (free tier)
- **Delivery**: Discord webhook + Telegram bot
- **Security**: Docker sandbox — zero access to host filesystem

## Why not OpenClaw?
OpenClaw is designed as a local persistent daemon (run via openclaw onboard).
It does not support Docker-native headless operation in the current stable release.
The file-based multi-agent handoff pattern we use mirrors OpenClaw's own
recommended agent communication approach.
