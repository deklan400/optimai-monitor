from services.ssh_client import get_status, get_reward_raw
from utils.parser import parse_reward


def check_vps(name, host):
    data = {
        "name": name,
        "host": host,
        "status": "down",
        "reward": None
    }

    status = get_status(host)
    data["status"] = status

    if status == "running":
        raw = get_reward_raw(host)

        if raw:
            reward = parse_reward(raw)
            data["reward"] = reward
        else:
            data["reward"] = None

    return data


def check_all_vps(vps_dict):
    results = []

    for name, host in vps_dict.items():
        print(f"[CHECK] {name} ({host})")

        try:
            result = check_vps(name, host)
        except Exception:
            result = {
                "name": name,
                "host": host,
                "status": "down",
                "reward": None
            }

        results.append(result)

    return results
