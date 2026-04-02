# AI Intelligence Engine

A multi-agent system that tracks competitor AI and technology activity across
Union Pacific, Norfolk Southern, and BNSF Railway, delivering a
**Strategic Weekly Digest** to Discord/Telegram.

## Architecture
- **Runtime**: OpenClaw (self-hosted, Dockerized)
- **Agents**: Scraper ×3, Orchestrator, Analyst, Formatter
- **LLM**: Google Gemini (free tier)
- **Delivery**: Discord webhook / Telegram bot

## Setup
See `docs/SETUP.md` for full instructions.

## Security
All agents run inside Docker with no access to host filesystem.
API keys are stored in `.env` (never committed to Git).