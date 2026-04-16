from services.ssh_client import get_status, get_reward_raw
from utils.parser import parse_reward


def check_vps(name, host):
    data = {
        "name": name,
        "host": host,
        "status": "down",
        "reward": None
    }

    # cek status
    status = get_status(host)
    data["status"] = status

    # kalau running → ambil reward
    if status == "running":
        raw = get_reward_raw(host)
        reward = parse_reward(raw)
        data["reward"] = reward

    return data


def check_all_vps(vps_dict):
    results = []

    for name, host in vps_dict.items():
        print(f"[CHECK] {name} ({host})")

        result = check_vps(name, host)
        results.append(result)

    return results
