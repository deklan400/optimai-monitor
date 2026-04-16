from services.ssh_client import get_node_status, get_node_reward
from utils.parser import parse_reward, is_valid_output


def check_vps(name, host):
    data = {
        "name": name,
        "host": host,
        "status": "down",
        "reward": None
    }

    # cek status
    status = get_node_status(host)
    data["status"] = status

    # cek reward kalau hidup
    if status == "running":
        raw = get_node_reward(host)

        if is_valid_output(raw):
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
