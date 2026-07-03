import re


def natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def success_rate(metrics):
    assignments = int((metrics or {}).get("assignments", 0))
    submitted = int((metrics or {}).get("submitted", 0))
    return (submitted / assignments * 100) if assignments else 0.0


def generate_ranking_report(current_data):
    ranked = sorted(
        current_data,
        key=lambda item: (
            -(item.get("metrics") or {}).get("submitted", 0),
            -(item.get("metrics") or {}).get("assignments", 0),
            natural_key(item.get("name", "")),
        ),
    )
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 RANKING HARIAN\n"]

    for position, item in enumerate(ranked, start=1):
        metrics = item.get("metrics") or {}
        icon = "✅" if item.get("status") == "running" else "❌"
        prefix = medals.get(position, f"{position}.")
        lines.append(
            f"{prefix} {item['name']} {icon} | "
            f"Submit:{metrics.get('submitted', 0)} | "
            f"Task:{metrics.get('assignments', 0)} | "
            f"SR:{success_rate(metrics):.1f}%"
        )

    return "\n".join(lines)


def generate_detail_report(item):
    metrics = item.get("metrics") or {}
    system = item.get("system") or {}
    icon = "✅" if item.get("status") == "running" else "❌"
    last_task = system.get("last_task") or "-"
    if len(last_task) > 120:
        last_task = last_task[:117] + "..."

    lines = [
        f"🔎 DETAIL {item.get('name', '-')}",
        "",
        f"Status       : {icon} {item.get('status', 'down')}",
        f"Host SSH     : {item.get('host', '-')}",
        f"Hostname     : {system.get('hostname', '-')}",
        f"Aktif sejak  : {system.get('active_since', '-')}",
        f"RAM          : {system.get('memory', '-')}",
        f"Disk /       : {system.get('disk', '-')}",
        f"Docker       : {system.get('docker', '-')}",
        "",
        "📊 Aktivitas hari ini",
        f"Task unik    : {metrics.get('assignments', 0)}",
        f"Submit sukses: {metrics.get('submitted', 0)}",
        f"Gagal final  : {metrics.get('failed', 0)}",
        f"Pending      : {metrics.get('pending', 0)}",
        f"Retry sukses : {metrics.get('retried', 0)}",
        f"Success rate : {success_rate(metrics):.1f}%",
        "",
        f"Task terakhir: {last_task}",
    ]
    return "\n".join(lines)
