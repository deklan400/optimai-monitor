def check_status_change(current_data, last_state):
    alerts = []
    new_state = {}

    for item in current_data:
        host = item["host"]
        status = item["status"]

        last_status = last_state.get(host)

        # simpan state baru
        new_state[host] = status

        # skip kalau pertama kali
        if last_status is None:
            continue

        # kalau berubah
        if status != last_status:
            if status == "running":
                alerts.append(f"✅ {host} : RUNNING KEMBALI")
            elif status == "down":
                alerts.append(f"⚠️ {host} : ❌ DOWN")

    return alerts, new_state
