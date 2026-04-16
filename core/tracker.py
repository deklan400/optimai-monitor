import json
import os

STATE_FILE = "data/state.json"
REWARD_FILE = "data/rewards.json"


def load_json(path):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except:
        pass


# ======================
# STATE (STATUS VPS)
# ======================
def load_state():
    return load_json(STATE_FILE)


def save_state(state):
    save_json(STATE_FILE, state)


# ======================
# REWARD
# ======================
def load_rewards():
    return load_json(REWARD_FILE)


def save_rewards(rewards):
    save_json(REWARD_FILE, rewards)
