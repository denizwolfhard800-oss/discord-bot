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


def get_stats(member_id: int) -> dict:
    """Return seconds spent in each status for a member, based on logged history."""
    entries = _load()
    member_entries = [e for e in entries if e["member_id"] == member_id]

    totals: dict[str, float] = {"online": 0, "idle": 0, "dnd": 0, "offline": 0}

    if not member_entries:
        return totals

    now = datetime.now(timezone.utc)

    for i, entry in enumerate(member_entries):
        status = entry["after"]
        start = datetime.fromisoformat(entry["timestamp"])
        end = datetime.fromisoformat(member_entries[i + 1]["timestamp"]) if i + 1 < len(member_entries) else now
        duration = (end - start).total_seconds()
        if status in totals:
            totals[status] += duration

    totals["first_seen"] = member_entries[0]["timestamp"]
    totals["total_entries"] = len(member_entries)
    return totals


def get_last_seen_online(member_id: int) -> datetime | None:
    """Return the timestamp of the most recent time this member went online, or None."""
    entries = _load()
    member_entries = [e for e in entries if e["member_id"] == member_id]
    for entry in reversed(member_entries):
        if entry["after"] == "online":
            return datetime.fromisoformat(entry["timestamp"])
    return None


def get_all_stats() -> list[dict]:
    """Return a list of per-member stats dicts, sorted by online seconds descending."""
    entries = _load()
    if not entries:
        return []

    from collections import defaultdict
    by_member: dict[int, list[dict]] = defaultdict(list)
    for e in entries:
        by_member[e["member_id"]].append(e)

    now = datetime.now(timezone.utc)
    results = []

    for member_id, member_entries in by_member.items():
        totals: dict[str, float] = {"online": 0, "idle": 0, "dnd": 0, "offline": 0}
        for i, entry in enumerate(member_entries):
            status = entry["after"]
            start = datetime.fromisoformat(entry["timestamp"])
            end = datetime.fromisoformat(member_entries[i + 1]["timestamp"]) if i + 1 < len(member_entries) else now
            duration = (end - start).total_seconds()
            if status in totals:
                totals[status] += duration
        results.append({
            "member_id": member_id,
            "member_name": member_entries[-1]["member_name"],
            **totals,
        })

    results.sort(key=lambda r: r["online"], reverse=True)
    return results


def _load() -> list[dict]:
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r") as f:
            return json.load(f)
    return []


def _save(entries: list[dict]) -> None:
    with open(HISTORY_PATH, "w") as f:
        json.dump(entries, f, indent=2)
