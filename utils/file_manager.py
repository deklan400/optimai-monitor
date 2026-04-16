import json
import os


def load_json_safe(path):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def save_json_safe(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[FILE ERROR] {e}")
