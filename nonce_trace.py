#!/usr/bin/env python3
"""Nonce Engine: hashes a real block header from solo.ckpool, one guess at a time.

Usage: ./nonce_trace.py [delay_seconds]   (default 0.3)
Reads BTC_ADDRESS and POOL_URL from the config file next to this script.
"""
import hashlib
import json
import os
import select
import socket
import struct
import sys
import time

DELAY = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
GREEN, RED, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"
BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def load_config():
    cfg = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip()
    return cfg


def address_program(addr):
    """Witness program (hex) of a bc1 address, to recognise your payout in the coinbase."""
    data = [BECH32.find(c) for c in addr.lower().split("1")[-1]][:-6]
    acc, bits, out = 0, 0, []
    for v in data[1:]:
        acc, bits = (acc << 5) | v, bits + 5
        while bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    return bytes(out).hex()


def sha256d(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def swap32(b):
    return b"".join(b[i:i + 4][::-1] for i in range(0, len(b), 4))


def target_from_bits(bits):
    exponent, mantissa = bits >> 24, bits & 0xFFFFFF
    return mantissa * (1 << (8 * (exponent - 3)))


def read_varint(b, i):
    n = b[i]
    if n < 0xFD:
        return n, i + 1
    size = {0xFD: 2, 0xFE: 4, 0xFF: 8}[n]
    return int.from_bytes(b[i + 1:i + 1 + size], "little"), i + 1 + size


def parse_coinbase(tx):
    """Block height (from the coinbase script) and the outputs (value, script hex)."""
    i = 4
    _, i = read_varint(tx, i)          # input count
    i += 36                            # prevout: 32 zero bytes + ffffffff
    script_len, i = read_varint(tx, i)
    script = tx[i:i + script_len]
    height = int.from_bytes(script[1:1 + script[0]], "little")
    i += script_len + 4                # script + sequence
    count, i = read_varint(tx, i)
    outputs = []
    for _ in range(count):
        value = int.from_bytes(tx[i:i + 8], "little")
        slen, i = read_varint(tx, i + 8)
        outputs.append((value, tx[i:i + slen].hex()))
        i += slen
    return height, outputs


class Stratum:
    def __init__(self, url, address):
        host, port = url.split("://")[-1].rsplit(":", 1)
        self.sock = socket.create_connection((host, int(port)), timeout=15)
        self.buf, self.next_id, self.address = b"", 1, address
        self.extranonce1, self.en2_size, self.job, self.new_job = None, 4, None, False
        self.send("mining.subscribe", ["nonce_trace/1.0"])
        self.send("mining.authorize", [address, "x"])
        while self.job is None or self.extranonce1 is None:
            self.handle(self.readline(block=True))

    def send(self, method, params):
        msg = {"id": self.next_id, "method": method, "params": params}
        self.next_id += 1
        self.sock.sendall((json.dumps(msg) + "\n").encode())

    def readline(self, block=False):
        while b"\n" not in self.buf:
            if not block and not select.select([self.sock], [], [], 0)[0]:
                return None
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("pool closed the connection")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return json.loads(line)

    def handle(self, msg):
        if msg is None:
            return
        if msg.get("id") == 1 and msg.get("result"):
            self.extranonce1, self.en2_size = msg["result"][1], msg["result"][2]
        elif msg.get("method") == "mining.notify":
            self.job, self.new_job = msg["params"], True

    def poll(self):
        while True:
            msg = self.readline()
            if msg is None:
                return
            self.handle(msg)


def build(job, extranonce1, en2_size, address):
    job_id, prevhash, coinb1, coinb2, branches, version, nbits, ntime, _ = job
    extranonce2 = "00" * en2_size
    coinbase = bytes.fromhex(coinb1 + extranonce1 + extranonce2 + coinb2)
    root = sha256d(coinbase)
    for branch in branches:
        root = sha256d(root + bytes.fromhex(branch))
    prev = swap32(bytes.fromhex(prevhash))
    header76 = (struct.pack("<I", int(version, 16)) + prev + root
                + struct.pack("<II", int(ntime, 16), int(nbits, 16)))
    height, outputs = parse_coinbase(coinbase)
    return {
        "job_id": job_id, "extranonce2": extranonce2, "ntime": ntime,
        "header76": header76, "bits": int(nbits, 16), "version": version,
        "prev": prev[::-1].hex(), "merkle": root[::-1].hex(), "time": int(ntime, 16),
        "txs": 2 ** len(branches), "height": height, "outputs": outputs,
        "coinbase_txid": sha256d(coinbase)[::-1].hex(),
    }


def zeros(h, colour=""):
    n = len(h) - len(h.lstrip("0"))
    return f"{GREEN}{BOLD}{h[:n]}{RESET}{colour}{h[n:]}{RESET}"


def main():
    cfg = load_config()
    address = cfg["BTC_ADDRESS"]
    program = address_program(address)
    pool = Stratum(cfg.get("POOL_URL", "stratum+tcp://solo.ckpool.org:3333"), address)

    best, guesses, jobs = None, 0, 0
    sys.stdout.write("\033[?25l")
    try:
        while True:
            pool.poll()
            if pool.new_job:
                work = build(pool.job, pool.extranonce1, pool.en2_size, address)
                target_hex = f"{target_from_bits(work['bits']):064x}"
                nonce, pool.new_job, jobs = 0, False, jobs + 1

            h = sha256d(work["header76"] + struct.pack("<I", nonce))[::-1].hex()
            guesses += 1
            best = h if best is None or h < best else best
            win = h <= target_hex
            if win:
                pool.send("mining.submit", [address, work["job_id"], work["extranonce2"],
                                            work["ntime"], f"{nonce:08x}"])

            payouts = []
            for value, script in work["outputs"]:
                if value == 0:
                    continue
                who = "you" if program and program in script else "pool"
                payouts.append(f"   {value / 1e8:.8f} BTC  ->  {who}")

            frame = [
                f"{BOLD}NONCE ENGINE{RESET}  {DIM}a real block attempt from solo.ckpool, slowed down{RESET}",
                "",
                f"{BOLD}0. Block body{RESET}  {DIM}(block {work['height']}, up to {work['txs']} transactions){RESET}",
                f"   coinbase txid   {work['coinbase_txid']}",
                *payouts,
                "",
                f"{BOLD}1. Block header{RESET}",
                f"   version         {work['version']}",
                f"   previous block  {work['prev']}",
                f"   merkle root     {work['merkle']}",
                f"   time            {work['time']}",
                f"   bits            {work['bits']:08x}",
                f"   nonce           {BOLD}{nonce}{RESET}  {DIM}<- changes every guess{RESET}",
                "",
                f"{BOLD}2. Hash it twice with SHA-256{RESET}",
                f"   hash            {zeros(h, GREEN if win else RED)}",
                f"   target          {zeros(target_hex, DIM)}",
                "",
                f"{BOLD}3. Is the hash below the target?{RESET}",
                f"   {GREEN}{BOLD}YES! Block found and submitted!{RESET}" if win
                else f"   {RED}No. Add 1 to the nonce and try again.{RESET}",
                "",
                f"   guesses shown   {guesses}    jobs received  {jobs}",
                f"   closest so far  {zeros(best, DIM)}",
                "",
                f"{DIM}The real miner does this ~790,000 times per second. Ctrl+C to stop.{RESET}",
            ]
            sys.stdout.write("\033[H\033[J" + "\n".join(frame) + "\n")
            sys.stdout.flush()
            if win:
                break
            nonce = (nonce + 1) % 2**32
            time.sleep(DELAY)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h")


if __name__ == "__main__":
    main()
