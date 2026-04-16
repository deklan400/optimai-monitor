from services.ssh_client import get_node_status, get_node_reward
from utils.parser import parse_reward


def check_vps(host):
    data = {
        "host": host,
        "status": "down",
        "reward": None
    }

    # cek status
    status = get_node_status(host)
    data["status"] = status

    # cek reward kalau hidup
    if status == "running":
        raw_reward = get_node_reward(host)
        reward = parse_reward(raw_reward)
        data["reward"] = reward

    return data


def check_all_vps(vps_list):
    results = []

    for host in vps_list:
        print(f"[CHECK] {host}")
        result = check_vps(host)
        results.append(result)

    return results
