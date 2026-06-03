import json
import os
from datetime import datetime, timezone

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


def save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_log_channel_id() -> int | None:
    config = load_config()
    if "log_channel_id" in config:
        return int(config["log_channel_id"])
    env_val = os.environ.get("LOG_CHANNEL_ID")
    if env_val and env_val != "0":
        return int(env_val)
    return None


def set_log_channel_id(channel_id: int) -> None:
    config = load_config()
    config["log_channel_id"] = channel_id
    save_config(config)


def get_warned_members() -> dict:
    """Return {member_id_str: iso_timestamp_of_warning}."""
    return load_config().get("warned_inactive", {})


def mark_member_warned(member_id: int) -> None:
    config = load_config()
    warned = config.get("warned_inactive", {})
    warned[str(member_id)] = datetime.now(timezone.utc).isoformat()
    config["warned_inactive"] = warned
    save_config(config)


def clear_member_warned(member_id: int) -> None:
    """Call this when a member comes back online so they can be warned again next time."""
    config = load_config()
    warned = config.get("warned_inactive", {})
    warned.pop(str(member_id), None)
    config["warned_inactive"] = warned
    save_config(config)
