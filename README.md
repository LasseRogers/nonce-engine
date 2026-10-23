# Nonce Engine

Raspberry Pi 2 solo-mining Bitcoin.

- `nonce-engine.service`: runs cpuminer against solo.ckpool.org
- `weekly-report.sh` + `.timer`: Telegram report every Sunday 10:00
- log2ram: keeps logs in RAM to reduce SD card wear
- `config.example`: copy to `config` and fill in (ignored by git)
