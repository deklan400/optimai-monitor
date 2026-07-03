import re


def _natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def get_account_reward(current_data):
    sorted_data = sorted(current_data, key=lambda item: _natural_key(item["name"]))

    for item in sorted_data:
        reward = item.get("reward")
        if item.get("status") == "running" and reward is not None:
            return reward, item["name"]

    return None, "-"


def _metrics_line(name, status, metrics):
    icon = "✅" if status == "running" else "❌"

    if not metrics or not metrics.get("available"):
        return f"{name} : {icon} | Task:- | Submit:- | Gagal:-"

    return (
        f"{name} : {icon} | "
        f"Task:{metrics.get('assignments', 0)} | "
        f"Submit:{metrics.get('submitted', 0)} | "
        f"Gagal:{metrics.get('failed', 0)} | "
        f"Pending:{metrics.get('pending', 0)} | "
        f"Retry:{metrics.get('retried', 0)}"
    )


def _format_reward(value, prefix=""):
    if value is None:
        return "-"
    return f"{prefix}{int(value)}"


def _append_node_metrics(report_lines, current_data):
    totals = {
        "assignments": 0,
        "submitted": 0,
        "failed": 0,
        "pending": 0,
        "retried": 0,
    }

    for item in sorted(current_data, key=lambda row: _natural_key(row["name"])):
        metrics = item.get("metrics")
        report_lines.append(_metrics_line(item["name"], item["status"], metrics))

        if metrics and metrics.get("available"):
            for key in totals:
                totals[key] += int(metrics.get(key, 0))

    return totals


def _append_activity_totals(report_lines, totals):
    report_lines.append("")
    report_lines.append("------------------------")
    report_lines.append(f"📦 Total Task Unik : {totals['assignments']}")
    report_lines.append(f"✅ Total Submit    : {totals['submitted']}")
    report_lines.append(f"❌ Gagal Final     : {totals['failed']}")
    report_lines.append(f"⏳ Masih Pending   : {totals['pending']}")
    report_lines.append(f"🔁 Retry Sukses    : {totals['retried']}")


def generate_report(current_data, last_snapshot, report_title="🔥 OPTIMAI REPORT (3 JAM)"):
    report_lines = [f"{report_title}\n"]
    totals = _append_node_metrics(report_lines, current_data)

    current_total, source_node = get_account_reward(current_data)
    previous_total = last_snapshot.get("account_total") if last_snapshot else None
    reward_diff = None
    if current_total is not None and isinstance(previous_total, (int, float)):
        reward_diff = max(0, current_total - previous_total)

    _append_activity_totals(report_lines, totals)
    report_lines.append(f"💰 Reward 3 Jam    : {_format_reward(reward_diff, '+')}")
    report_lines.append(f"💰 Total Akun      : {_format_reward(current_total)}")
    report_lines.append(f"📍 Sumber Saldo    : {source_node}")
    return "\n".join(report_lines)


def generate_manual_report(current_data, report_title="⚡ OPTIMAI CHECK MANUAL"):
    report_lines = [f"{report_title}\n"]
    totals = _append_node_metrics(report_lines, current_data)
    current_total, source_node = get_account_reward(current_data)
    _append_activity_totals(report_lines, totals)
    report_lines.append(f"💰 Total Akun      : {_format_reward(current_total)}")
    report_lines.append(f"📍 Sumber Saldo    : {source_node}")
    return "\n".join(report_lines)


def generate_daily_report(current_data, report_title):
    report_lines = [f"{report_title}\n"]
    totals = _append_node_metrics(report_lines, current_data)
    current_total, source_node = get_account_reward(current_data)
    _append_activity_totals(report_lines, totals)
    report_lines.append(f"💰 Total Akun      : {_format_reward(current_total)}")
    report_lines.append(f"📍 Sumber Saldo    : {source_node}")
    return "\n".join(report_lines)
