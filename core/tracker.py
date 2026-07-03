import json
import os
import time

STATE_FILE = "data/state.json"
REWARD_FILE = "data/rewards.json"
DAILY_STATE_FILE = "data/daily_report_state.json"


def load_json(path):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_json(path, data):
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[TRACKER ERROR] {e}")


def load_state():
    return load_json(STATE_FILE)


def save_state(state):
    save_json(STATE_FILE, state)


def load_reward_snapshot():
    data = load_json(REWARD_FILE)
    total = data.get("account_total")

    if not isinstance(total, (int, float)):
        return {}

    return data


def save_reward_snapshot(account_total, source_node):
    if not isinstance(account_total, (int, float)):
        return

    save_json(
        REWARD_FILE,
        {
            "account_total": float(account_total),
            "source_node": source_node or "-",
            "updated_at": int(time.time()),
        },
    )


def load_daily_report_state():
    return load_json(DAILY_STATE_FILE)


def save_daily_report_state(active_date):
    save_json(
        DAILY_STATE_FILE,
        {
            "active_date": str(active_date),
            "updated_at": int(time.time()),
        },
    )


# Alias kompatibilitas untuk kode lama.
def load_rewards():
    return load_reward_snapshot()


def save_rewards(rewards):
    if not isinstance(rewards, dict):
        return

    save_reward_snapshot(
        rewards.get("account_total"),
        rewards.get("source_node", "-"),
    )
