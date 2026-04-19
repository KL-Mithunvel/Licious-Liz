"""
f1_logger.py — Session event logger.

Appends one JSON record per event to session_log.jsonl in the project root.
Each record has at minimum: ts (ISO-8601), event (string).
"""

import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("session_log.jsonl")


def _write(event: str, **fields) -> None:
    record = {"ts": datetime.now().isoformat(), "event": event, **fields}
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def log_session_loaded(label: str) -> None:
    _write("session_loaded", label=label)


def log_replay_started(label: str, speed: float) -> None:
    _write("replay_started", label=label, speed=speed)


def log_replay_paused(elapsed_s: int) -> None:
    _write("replay_paused", elapsed_s=elapsed_s)


def log_replay_finished(label: str) -> None:
    _write("replay_finished", label=label)


def log_live_connected(session_key: int) -> None:
    _write("live_connected", session_key=session_key)


def log_error(message: str) -> None:
    _write("error", message=message)
