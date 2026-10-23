#!/usr/bin/env bash
# Sends a weekly Nonce Engine report to Telegram.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/config"

LOG="$(journalctl -u nonce-engine --since "7 days ago" --no-pager -o cat 2>/dev/null || true)"

TOTAL="$(grep -oP 'thread \d+: \K\d+(?= hashes)' <<<"$LOG" | awk '{s+=$1} END {printf "%.1f", s/1e9}')"
SPEED="$(grep -oP '[\d.]+(?= khash/s)' <<<"$LOG" | awk -v t="$THREADS" '{s+=$1; n++} END {if (n) printf "%.0f", s/n*t; else print 0}')"
ACCEPTED="$(grep -c 'accepted' <<<"$LOG" || true)"
WEEK="$(date +%V)"
STATUS="$(systemctl is-active nonce-engine || true)"
UPTIME="$(uptime -p)"
TEMP="$(vcgencmd measure_temp | grep -oP '[\d.]+')"

MSG="Nonce Engine weekly report, week ${WEEK}

Status: ${STATUS}
Uptime: ${UPTIME#up }
Guesses this week: ${TOTAL} billion
Average speed: ${SPEED} kH/s
Accepted near-misses: ${ACCEPTED}
Temperature: ${TEMP} °C

Still searching for that one lucky nonce."

curl -sS --fail "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MSG}" > /dev/null
