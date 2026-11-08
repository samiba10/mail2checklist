#!/bin/sh
# Runs the Gmail poller in the background and the web app in the foreground.
# If the poller crashes it is restarted; if the web app exits, the container exits.
set -e

(
  while true; do
    python -m app.poller || echo "poller exited with $?, restarting in 30s"
    sleep 30
  done
) &

exec uvicorn app.web:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips='*'
