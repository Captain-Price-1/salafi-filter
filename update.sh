#!/bin/bash
# Re-run the scraper (incremental) and rebuild the HTML.
# This is the script the launchd agent invokes every 5 hours.
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p logs
LOG="logs/update-$(date +%Y%m%d).log"

{
  echo ""
  echo "=== run started at $(date) ==="
  source .venv/bin/activate
  python3 scrape.py
  python3 build_html.py
  echo "=== run finished at $(date) ==="
} >> "$LOG" 2>&1
