import json
import os

STATE_FILE = "data/state.json"
REWARD_FILE = "data/rewards.json"


def load_json(file_path):
    if not os.path.exists(file_path):
        return {}

    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except:
            return {}


def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def load_state():
    return load_json(STATE_FILE)


def save_state(state):
    save_json(STATE_FILE, state)


def load_rewards():
    return load_json(REWARD_FILE)


def save_rewards(rewards):
    save_json(REWARD_FILE, rewards)
