def _clean_reason(reason):
    reason = (reason or "").strip()
    if not reason:
        return "Belum terdeteksi. Cek detail/log VPS."
    return reason[:700]


def check_status_change(current_data, last_state):
    alerts = []
    new_state = {}

    for item in current_data:
        name = item["name"]
        status = item["status"]

        last_status = last_state.get(name)

        # simpan state baru
        new_state[name] = status

        # pertama kali → skip
        if last_status is None:
            continue

        # kalau berubah
        if status != last_status:
            if status == "running":
                alerts.append(f"✅ {name} : RUNNING KEMBALI")
            else:
                reason = _clean_reason(item.get("down_reason"))
                alerts.append(f"⚠️ {name} : ❌ DOWN\nPenyebab: {reason}")

    return alerts, new_state
