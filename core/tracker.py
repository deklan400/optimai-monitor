from utils.file_manager import load_json_safe, save_json_safe

STATE_FILE = "data/state.json"
REWARD_FILE = "data/rewards.json"


def load_state():
    return load_json_safe(STATE_FILE)


def save_state(state):
    save_json_safe(STATE_FILE, state)


def load_rewards():
    return load_json_safe(REWARD_FILE)


def save_rewards(rewards):
    save_json_safe(REWARD_FILE, rewards)
