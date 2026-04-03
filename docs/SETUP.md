# AI Intelligence Engine — Setup Guide

Complete instructions to get the system running from scratch.
Estimated setup time: 20 minutes.

## Prerequisites

Install these on your Windows machine before starting:

| Tool | Version | Download |
|------|---------|----------|
| Git | 2.x+ | https://git-scm.com/download/win |
| Docker Desktop | 4.x+ | https://www.docker.com/products/docker-desktop |
| VS Code | Latest | https://code.visualstudio.com |

Verify each is installed:
\\\powershell
git --version
docker --version
\\\

## Step 1 — Clone the Repository

\\\powershell
git clone https://github.com/YOUR-USERNAME/Ai-intelligence-engine.git
cd Ai-intelligence-engine
\\\

## Step 2 — Configure Secrets

Copy the template and fill in your real values:

\\\powershell
Copy-Item .env.example .env
notepad .env
\\\

Fill in these values:

\\\env
# Get free at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_key_here

# Discord: Server Settings > Integrations > Webhooks > New Webhook > Copy URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN

# Optional Telegram delivery
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
\\\

## Step 3 — Build and Run

\\\powershell
# Build all Docker images (first build takes ~5 minutes — Chromium downloads)
docker compose -f docker/docker-compose.yml build

# Start the pipeline scheduler
docker compose -f docker/docker-compose.yml up pipeline-scheduler
\\\

On startup, the system immediately runs one pipeline test.
Check your Discord channel — you should see the first digest within 2-3 minutes.

## Step 4 — Verify It's Working

Watch the live logs:
\\\powershell
docker compose -f docker/docker-compose.yml logs --follow pipeline-scheduler
\\\

You should see:
\\\
[CABAL] Starting orchestration run...
[UP Scout] Launching headless browser...
[UP Scout] Found X relevant articles.
[DAEDALUS] Analyzing 1/X: Article title...
[HERALD] Sent X articles to Discord.
PIPELINE COMPLETED SUCCESSFULLY
\\\

## Step 5 — Weekly Automation

The pipeline runs automatically every Monday at 07:00 UTC.
Keep Docker Desktop running and the container will handle the rest.

To stop: \docker compose -f docker/docker-compose.yml down\
To restart: \docker compose -f docker/docker-compose.yml up -d pipeline-scheduler\

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No articles found | Keywords may not match current headlines — check scraper AI_TECH_KEYWORDS |
| Gemini 429 error | Free tier rate limit hit — retry logic handles this automatically |
| Discord not receiving | Verify DISCORD_WEBHOOK_URL in .env is correct |
| Container won't start | Run \docker compose build --no-cache\ to rebuild fresh |

## Pipeline Data Files

All intermediate data lives in the Docker volume at \/app/data/pipeline/\:

| File | Written by | Read by |
|------|-----------|---------|
| raw_articles.json | CABAL | audit only |
| scored_articles.json | CABAL | DAEDALUS |
| analyzed_articles.json | DAEDALUS | HERALD |
| seen_article_ids.json | CABAL | CABAL (dedup memory) |
