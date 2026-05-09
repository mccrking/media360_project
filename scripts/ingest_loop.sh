#!/usr/bin/env bash
# Simple ingestion loop for development/demo. Run inside project container.
set -e
INTERVAL_SECONDS=${INTERVAL_SECONDS:-300}
while true; do
  echo "[ingest_loop] running ingestion at $(date -u)"
  python /opt/project/scripts/run_batch_insert.py || echo "ingest failed"
  sleep "$INTERVAL_SECONDS"
done
