import json
import os
import threading

from config import VPS_LIST

VPS_FILE = "data/vps_list.json"
_LOCK = threading.Lock()


def ensure_vps_file():
    os.makedirs("data", exist_ok=True)

    if os.path.exists(VPS_FILE):
        return

    initial_data = {}
    for name, host in VPS_LIST.items():
        if "IP_VPS_" in host:
            continue
        initial_data[name] = host

    with open(VPS_FILE, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, indent=4)


def load_vps():
    ensure_vps_file()

    with _LOCK:
        try:
            with open(VPS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return {}


def save_vps(vps_dict):
    ensure_vps_file()

    with _LOCK:
        with open(VPS_FILE, "w", encoding="utf-8") as f:
            json.dump(vps_dict, f, indent=4)


def add_vps(name, host):
    data = load_vps()
    data[name] = host
    save_vps(data)


def delete_vps(name):
    data = load_vps()
    if name not in data:
        return False
    del data[name]
    save_vps(data)
    return True


def update_vps(name, host):
    data = load_vps()
    if name not in data:
        return False
    data[name] = host
    save_vps(data)
    return True
