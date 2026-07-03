import re

from services.ssh_client import (
    get_node_metrics,
    get_node_system_detail,
    get_reward_raw,
    get_status,
)
from utils.parser import parse_reward


def _natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def check_vps(
    name,
    host,
    metrics_since=None,
    metrics_until=None,
    include_details=False,
):
    data = {
        "name": name,
        "host": host,
        "status": "down",
        "reward": None,
        "metrics": None,
        "system": None,
    }

    data["status"] = get_status(host)

    if metrics_since:
        data["metrics"] = get_node_metrics(
            host,
            since_utc=metrics_since,
            until_utc=metrics_until,
        )

    if include_details:
        data["system"] = get_node_system_detail(host)

    return data


def check_all_vps(
    vps_dict,
    include_reward=False,
    metrics_since=None,
    metrics_until=None,
    include_details=False,
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
                include_details=include_details,
            )
        except Exception:
            result = {
                "name": name,
                "host": host,
                "status": "down",
                "reward": None,
                "metrics": None,
                "system": None,
            }

        results.append(result)

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
