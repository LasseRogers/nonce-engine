#!/usr/bin/env bash
# Installs log2ram to keep /var/log in RAM and reduce SD card wear.
set -euo pipefail

if systemctl list-unit-files log2ram.service 2>/dev/null | grep -q log2ram; then
  echo "log2ram is already installed."
  systemctl --no-pager status log2ram | head -3 || true
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Shrinking the journal so it fits in RAM..."
sudo journalctl --vacuum-size=32M

echo "Downloading log2ram..."
curl -fsSL https://github.com/azlux/log2ram/archive/master.tar.gz | tar xz -C "$TMP"

echo "Installing..."
cd "$TMP/log2ram-master"
chmod +x install.sh
sudo ./install.sh

echo
echo "Done. Reboot to activate log2ram:  sudo reboot"
echo "Then check it with:                df -h | grep log2ram"
