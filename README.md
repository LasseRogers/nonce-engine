# Nonce Engine

Solo-mining Bitcoin on a Raspberry Pi (built for a Pi 2, works on any Debian-based Linux).

- `setup.sh`: builds cpuminer and installs everything. Run it, fill in `config`, run it again
- `nonce-engine.service`: runs cpuminer against solo.ckpool.org
- `weekly-report.sh` + `.timer`: Telegram report every Sunday 10:00
- `log2ram_installer.sh`: optional, keeps logs in RAM to reduce SD card wear
- `rpi_connect_installer.sh`: optional, remote shell access from any browser at https://connect.raspberrypi.com/
- `config.example`: copied to `config` by `setup.sh` (ignored by git)

## Setup

```bash
git clone https://github.com/LasseRogers/nonce-engine
cd nonce-engine
./setup.sh
```

## Commands

```bash
journalctl -u nonce-engine -f       # watch the miner live
sudo systemctl stop nonce-engine    # pause mining
sudo systemctl start nonce-engine   # resume mining
vcgencmd measure_temp               # check the temperature
./nonce_trace.py                    # watch the mining loop step by step
./nonce_trace.py 0.05               # same, faster
```