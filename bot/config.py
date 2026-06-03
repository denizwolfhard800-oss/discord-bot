import json
import os

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
