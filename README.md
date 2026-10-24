# Nonce Engine

Raspberry Pi 2 solo-mining Bitcoin.

- `nonce-engine.service`: runs cpuminer against solo.ckpool.org
- `weekly-report.sh` + `.timer`: Telegram report every Sunday 10:00
- `log2ram_installer.sh`: installs log2ram, which keeps logs in RAM to reduce SD card wear
- `rpi_connect_installer.sh`: installs Raspberry Pi Connect for remote shell access from any browser at https://connect.raspberrypi.com/
- `config.example`: copy to `config` and fill in (ignored by git)

## Commands

```bash
journalctl -u nonce-engine -f       # watch the miner live
sudo systemctl stop nonce-engine    # pause mining
sudo systemctl start nonce-engine   # resume mining
vcgencmd measure_temp               # check the temperature
./nonce_trace.py                    # watch the mining loop step by step
./nonce_trace.py 0.05               # same, faster
```
