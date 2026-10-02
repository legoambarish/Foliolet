"""Authenticated, recursive First-Seen Integrity agent.

python watch.py FOLDER --config .local-data/agent.json [--once]

The config contains agentId, secret and apiUrl (default http://localhost:8080).
Only stable sampled bytes are reported; this does not attest issuer truth.
A durable outbox retries the identical signed record after network failures.
"""
import argparse
import hashlib
import hmac
import json
import os
import queue
import struct
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from Crypto.Hash import keccak
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

ZERO = "0x" + "00" * 32


def encode(*fields):
    parts = []
    for field in fields:
        data = str(field).encode("utf-8")
        parts.extend((struct.pack(">I", len(data)), data))
    return b"".join(parts)


def message(record):
    return encode("first-seen-v1", record["agentId"], record["itemId"], record["filename"], record["sha256"],
                  int(datetime.fromisoformat(record["observedAt"].replace("Z", "+00:00")).timestamp()),
                  record["sequence"], record["previousDigest"])


def sha256_of_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class Agent:
    def __init__(self, folder, config, state_path):
        self.folder = Path(folder).resolve()
        self.config = config
        self.state_path = Path(state_path).resolve()
        self.lock = threading.Lock()
        self.state = json.loads(self.state_path.read_text(encoding="utf-8")) if self.state_path.exists() else {
            "agentId": config["agentId"], "sequence": 0, "digest": ZERO, "items": {}, "pending": None}
        if self.state["agentId"] != config["agentId"]:
            raise ValueError("Agent configuration differs from the persisted state")

    def save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        os.replace(temp, self.state_path)

    def flush(self):
        pending = self.state["pending"]
        if not pending:
            return True
        record = pending["record"]
        try:
            response = requests.post(self.config.get("apiUrl", "http://localhost:8080").rstrip("/") + "/api/integrity/observations",
                                     json=record, timeout=10)
            response.raise_for_status()
            reply = response.json()
            expected_digest = "0x" + keccak.new(digest_bits=256, data=message(record)).hexdigest()
            if reply["digest"] != expected_digest or reply["sequence"] != record["sequence"]:
                raise ValueError("Unexpected observation acknowledgement")
            self.state["sequence"] = record["sequence"]
            self.state["digest"] = reply["digest"]
            self.state["items"][pending["relative"]]["lastHash"] = record["sha256"]
            self.state["items"][pending["relative"]]["observationId"] = reply["observationId"]
            self.state["pending"] = None
            self.save()
            print(f"Observed {record['filename']}: {record['sha256'][:12]}… (record {reply['observationId']})", flush=True)
            return True
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Observation retained for retry: {type(exc).__name__}", flush=True)
            return False

    def report(self, path):
        with self.lock:
            if not self.flush():
                return False
            path = Path(path).resolve()
            if not path.is_file() or path == self.state_path or path == self.state_path.with_suffix(".tmp"):
                return True
            try:
                relative = str(path.relative_to(self.folder))
                before = path.stat()
                fingerprint = sha256_of_file(path)
                time.sleep(0.35)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    return False
            except (OSError, ValueError):
                return False
            item = self.state["items"].setdefault(relative, {"id": str(uuid.uuid4()), "lastHash": None})
            if item["lastHash"] == fingerprint:
                return True
            record = {"agentId": self.config["agentId"], "itemId": item["id"], "filename": path.name,
                      "sha256": fingerprint, "observedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                      "sequence": self.state["sequence"] + 1, "previousDigest": self.state["digest"]}
            record["signature"] = hmac.new(bytes.fromhex(self.config["secret"].removeprefix("0x")), message(record), hashlib.sha256).hexdigest()
            self.state["pending"] = {"record": record, "relative": relative}
            self.save()
            return self.flush()


class IntakeHandler(FileSystemEventHandler):
    def __init__(self, pending):
        self.pending = pending

    def on_created(self, event):
        if not event.is_directory:
            self.pending.put(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.pending.put(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.pending.put(event.dest_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder")
    parser.add_argument("--config", required=True)
    parser.add_argument("--state")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        parser.error("The watched folder must exist")
    # Never observe the agent's own secret/configuration as a document.
    if config_path.is_relative_to(folder):
        parser.error("Keep the secret configuration outside the watched folder")
    state_path = args.state or str(config_path.with_name(config["agentId"] + "-state.json"))
    agent = Agent(folder, config, state_path)
    pending = queue.Queue()
    observer = None
    if not args.once:
        observer = Observer()
        observer.schedule(IntakeHandler(pending), str(folder), recursive=True)
        observer.start()
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            pending.put(str(path))
    print(f"Sampling {folder} recursively. First-seen means server-received observation, not creation.", flush=True)
    failed = False
    try:
        while not args.once or not pending.empty():
            try:
                path = pending.get(timeout=2)
            except queue.Empty:
                with agent.lock:
                    agent.flush()
                continue
            if not agent.report(path):
                failed = True
                if not args.once:
                    time.sleep(2)
                    pending.put(path)
        return 1 if failed else 0
    except KeyboardInterrupt:
        return 0
    finally:
        if observer:
            observer.stop()
            observer.join()


if __name__ == "__main__":
    raise SystemExit(main())
