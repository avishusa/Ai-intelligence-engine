"""
pipeline/run_pipeline.py
WHY THIS FILE:
  Instead of manually running 5 scripts in order, one command
  triggers the full pipeline: scrape → orchestrate → analyze → deliver.
  This is what your cron scheduler will call every Monday at 7AM.
"""

import subprocess
import sys
from datetime import datetime

STEPS = [
    ("CABAL (Orchestrator + Scrapers)", "/app/agents/orchestrator/orchestrator.py"),
    ("DAEDALUS (Gemini Analyst)",       "/app/agents/analyst/analyst.py"),
    ("HERALD (Formatter + Delivery)",   "/app/agents/formatter/formatter.py"),
]

def run_pipeline():
    print("\n" + "=" * 60)
    print(f"AI INTELLIGENCE ENGINE — PIPELINE START")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    for step_name, script_path in STEPS:
        print(f"\n▶  Running: {step_name}")
        print("-" * 40)

        result = subprocess.run(
            [sys.executable, script_path],
            # WHY not capture_output? We want logs streaming live to Docker logs.
            # This way `docker logs` shows real-time progress.
        )

        if result.returncode != 0:
            print(f"\n❌ PIPELINE FAILED at: {step_name}")
            print("Check the logs above for details.")
            sys.exit(1)
        else:
            print(f"✓ {step_name} completed successfully.")

    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE — Digest delivered.")
    print("=" * 60)

if __name__ == "__main__":
    run_pipeline()