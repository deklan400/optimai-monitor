import json
import os
import threading
import time
from datetime import date, timedelta

HISTORY_FILE = "data/history.json"
_HISTORY_LOCK = threading.Lock()


def _load_unlocked():
    if not os.path.exists(HISTORY_FILE):
        return {"days": {}}

    try:
        with open(HISTORY_FILE, "r") as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {"days": {}}

    if not isinstance(data, dict):
        return {"days": {}}

    days = data.get("days")
    if not isinstance(days, dict):
        days = {}
    return {"days": days}


def _save_unlocked(data):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    temp_path = f"{HISTORY_FILE}.tmp"
    with open(temp_path, "w") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temp_path, HISTORY_FILE)


def _metric_value(metrics, key):
    value = metrics.get(key, 0) if isinstance(metrics, dict) else 0
    return int(value) if isinstance(value, (int, float)) else 0


def save_daily_snapshot(day_key, current_data, account_total=None, source_node="-"):
    """Simpan snapshot kumulatif satu hari. Data unavailable tidak menimpa data lama."""
    with _HISTORY_LOCK:
        history = _load_unlocked()
        existing = history["days"].get(day_key, {})
        nodes = dict(existing.get("nodes", {}))

        for item in current_data:
            name = item.get("name")
            if not name:
                continue

            metrics = item.get("metrics")
            previous = nodes.get(name, {})
            node_data = {
                "status": item.get("status", previous.get("status", "down")),
                "assignments": previous.get("assignments", 0),
                "submitted": previous.get("submitted", 0),
                "failed": previous.get("failed", 0),
                "pending": previous.get("pending", 0),
                "retried": previous.get("retried", 0),
            }

            if metrics and metrics.get("available"):
                for key in ("assignments", "submitted", "failed", "pending", "retried"):
                    node_data[key] = _metric_value(metrics, key)

            nodes[name] = node_data

        totals = {
            key: sum(_metric_value(node, key) for node in nodes.values())
            for key in ("assignments", "submitted", "failed", "pending", "retried")
        }

        history["days"][day_key] = {
            "updated_at": int(time.time()),
            "account_total": account_total if account_total is not None else existing.get("account_total"),
            "source_node": source_node if source_node != "-" else existing.get("source_node", "-"),
            "nodes": nodes,
            "totals": totals,
        }
        _save_unlocked(history)


def get_recent_days(limit=7):
    with _HISTORY_LOCK:
        history = _load_unlocked()

    keys = sorted(history["days"].keys(), reverse=True)[:limit]
    return [(key, history["days"][key]) for key in keys]


def get_day(day_key):
    with _HISTORY_LOCK:
        return _load_unlocked()["days"].get(day_key)


def get_week_summary(end_date=None, days=7):
    if end_date is None:
        end_date = date.today()

    wanted = [(end_date - timedelta(days=offset)).isoformat() for offset in range(days)]

    with _HISTORY_LOCK:
        stored = _load_unlocked()["days"]

    selected = [(key, stored[key]) for key in wanted if key in stored]
    node_totals = {}
    totals = {key: 0 for key in ("assignments", "submitted", "failed", "pending", "retried")}

    for _, day_data in selected:
        for key in totals:
            totals[key] += _metric_value(day_data.get("totals", {}), key)

        for name, node in day_data.get("nodes", {}).items():
            aggregate = node_totals.setdefault(
                name,
                {key: 0 for key in ("assignments", "submitted", "failed", "pending", "retried")},
            )
            for key in aggregate:
                aggregate[key] += _metric_value(node, key)

    return {
        "days_found": len(selected),
        "dates": [key for key, _ in selected],
        "totals": totals,
        "nodes": node_totals,
    }
