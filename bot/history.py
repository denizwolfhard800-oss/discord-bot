import json
import os
from datetime import datetime, timezone

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "presence_history.json")
MAX_ENTRIES = 10_000


def append_entry(member_id: int, member_name: str, before: str, after: str) -> None:
    entries = _load()
    entries.append({
        "member_id": member_id,
        "member_name": member_name,
        "before": before,
        "after": after,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    _save(entries)


def get_entries(member_id: int, limit: int = 10) -> list[dict]:
    entries = _load()
    member_entries = [e for e in entries if e["member_id"] == member_id]
    return member_entries[-limit:][::-1]


def _load() -> list[dict]:
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r") as f:
            return json.load(f)
    return []


def _save(entries: list[dict]) -> None:
    with open(HISTORY_PATH, "w") as f:
        json.dump(entries, f, indent=2)
