import re

from services.ssh_client import get_node_metrics, get_reward_raw, get_status
from utils.parser import parse_reward


def _natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def check_vps(name, host, metrics_since=None, metrics_until=None):
    data = {
        "name": name,
        "host": host,
        "status": "down",
        "reward": None,
        "metrics": None,
    }

    status = get_status(host)
    data["status"] = status

    # Journal masih bisa dibaca meski service sedang inactive, selama VPS dan
    # SSH masih dapat diakses. Ini penting untuk laporan akhir harian.
    if metrics_since:
        data["metrics"] = get_node_metrics(
            host,
            since_utc=metrics_since,
            until_utc=metrics_until,
        )

    return data


def check_all_vps(
    vps_dict,
    include_reward=False,
    metrics_since=None,
    metrics_until=None,
):
    results = []

    for name, host in sorted(vps_dict.items(), key=lambda item: _natural_key(item[0])):
        print(f"[CHECK] {name} ({host})")

        try:
            result = check_vps(
                name,
                host,
                metrics_since=metrics_since,
                metrics_until=metrics_until,
            )
        except Exception:
            result = {
                "name": name,
                "host": host,
                "status": "down",
                "reward": None,
                "metrics": None,
            }

        results.append(result)

    # Semua node memakai akun OptimAI yang sama. Ambil saldo dari satu node
    # running pertama saja agar saldo akun tidak dihitung berkali-kali.
    if include_reward:
        for item in results:
            if item["status"] != "running":
                continue

            raw = get_reward_raw(item["host"])
            reward = parse_reward(raw) if raw else None
            if reward is not None:
                item["reward"] = reward
                break

    return results
