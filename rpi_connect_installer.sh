#!/usr/bin/env bash
# Installs Raspberry Pi Connect (remote shell from any browser at connect.raspberrypi.com).
set -euo pipefail

if ! command -v rpi-connect >/dev/null 2>&1; then
  echo "Installing rpi-connect-lite..."
  sudo apt install -y rpi-connect-lite
else
  echo "rpi-connect is already installed."
fi

echo "Starting Raspberry Pi Connect..."
rpi-connect on

echo "Keeping it running when you're logged out..."
sudo loginctl enable-linger "$USER"

if rpi-connect status 2>/dev/null | grep -qi "signed in: yes"; then
  echo "Already signed in."
else
  echo
  echo "Open the link below and log in with your Raspberry Pi ID:"
  rpi-connect signin
fi

echo
echo "Done. Connect at https://connect.raspberrypi.com -> $(hostname) -> Remote shell"
