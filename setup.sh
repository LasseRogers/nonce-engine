#!/usr/bin/env bash
# Builds cpuminer and installs the Nonce Engine services. Can be re-run.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
CPUMINER_DIR="$(dirname "$DIR")/cpuminer"
MINER="$CPUMINER_DIR/minerd"
RUN_USER="$(id -un)"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"

if [[ $EUID -eq 0 ]]; then
  echo "Don't run this with sudo."
  exit 1
fi

# systemd chokes on spaces in paths
if [[ "$DIR" == *" "* ]]; then
  echo "Repo path can't contain spaces: $DIR"
  exit 1
fi

chmod +x "$DIR"/*.sh "$DIR/nonce_trace.py"

# cpuminer lives next to this repo
if [[ -x "$MINER" ]]; then
  echo "cpuminer already built."
else
  echo "Installing build tools..."
  sudo apt-get update
  sudo apt-get install -y git build-essential automake autoconf libcurl4-openssl-dev

  if [[ ! -d "$CPUMINER_DIR" ]]; then
    echo "Downloading cpuminer..."
    git clone https://github.com/pooler/cpuminer "$CPUMINER_DIR"
  fi

  echo "Building cpuminer..."
  (cd "$CPUMINER_DIR" && ./autogen.sh && ./configure CFLAGS="-O3" && make -j"$(nproc)")
fi

if [[ ! -f "$DIR/config" ]]; then
  cp "$DIR/config.example" "$DIR/config"
  chmod 600 "$DIR/config"
  echo "Created config. Fill it in and run ./setup.sh again."
  exit 0
fi

source "$DIR/config"

if [[ -z "${BTC_ADDRESS:-}" || "$BTC_ADDRESS" == "bc1qyouraddresshere" ]]; then
  echo "BTC_ADDRESS not set in config."
  exit 1
fi

# default to all cores but one
if [[ -z "${THREADS:-}" ]]; then
  THREADS=$(( $(nproc) > 1 ? $(nproc) - 1 : 1 ))
  if grep -q '^THREADS=' "$DIR/config"; then
    sed -i "s/^THREADS=.*/THREADS=$THREADS/" "$DIR/config"
  else
    echo "THREADS=$THREADS" >> "$DIR/config"
  fi
  echo "Using $THREADS threads."
fi

echo "Installing services..."
# fill in {{USER}}, {{DIR}} and {{MINER}} in the unit files
render() {
  sed -e "s|{{USER}}|$RUN_USER|g" \
      -e "s|{{DIR}}|$DIR|g" \
      -e "s|{{MINER}}|$MINER|g" \
      "$DIR/$1" | sudo tee "$SYSTEMD_DIR/$1" > /dev/null
}
render nonce-engine.service
render weekly-report.service
sudo cp "$DIR/weekly-report.timer" "$SYSTEMD_DIR/"
sudo systemctl daemon-reload

echo "Starting miner..."
sudo systemctl enable nonce-engine
sudo systemctl restart nonce-engine

if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "Enabling weekly report..."
  sudo systemctl enable --now weekly-report.timer
else
  echo "No Telegram details, skipping weekly report."
fi

echo
echo "Done. Check it with:  journalctl -u nonce-engine -f"