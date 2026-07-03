from datetime import date

from core.ranking import natural_key


def generate_daily_history_report(recent_days):
    lines = ["📅 RIWAYAT HARIAN\n"]
    if not recent_days:
        lines.append("Belum ada data. Jalankan Check Manual terlebih dahulu.")
        return "\n".join(lines)

    for day_key, day_data in recent_days:
        totals = day_data.get("totals", {})
        try:
            label = date.fromisoformat(day_key).strftime("%d-%m-%Y")
        except ValueError:
            label = day_key
        lines.append(
            f"{label} | Task:{totals.get('assignments', 0)} | "
            f"Submit:{totals.get('submitted', 0)} | "
            f"Gagal:{totals.get('failed', 0)} | "
            f"Pending:{totals.get('pending', 0)}"
        )

    return "\n".join(lines)


def generate_weekly_history_report(summary):
    totals = summary.get("totals", {})
    lines = [
        "📈 RIWAYAT 7 HARI",
        "",
        f"Data tersedia : {summary.get('days_found', 0)}/7 hari",
        f"📦 Total Task   : {totals.get('assignments', 0)}",
        f"✅ Total Submit : {totals.get('submitted', 0)}",
        f"❌ Gagal Final  : {totals.get('failed', 0)}",
        f"⏳ Pending      : {totals.get('pending', 0)}",
        f"🔁 Retry sukses : {totals.get('retried', 0)}",
        "",
        "🏆 TOP NODE 7 HARI",
    ]

    ranked = sorted(
        summary.get("nodes", {}).items(),
        key=lambda pair: (-pair[1].get("submitted", 0), natural_key(pair[0])),
    )

    if not ranked:
        lines.append("Belum ada data mingguan.")
    else:
        for position, (name, metrics) in enumerate(ranked[:10], start=1):
            lines.append(
                f"{position}. {name} | Submit:{metrics.get('submitted', 0)} | "
                f"Task:{metrics.get('assignments', 0)} | "
                f"Gagal:{metrics.get('failed', 0)}"
            )

    return "\n".join(lines)
