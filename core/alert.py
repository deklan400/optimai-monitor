def check_status_change(current_data, last_state):
    alerts = []
    new_state = {}

    for item in current_data:
        name = item["name"]
        status = item["status"]

        last_status = last_state.get(name)

        # simpan state baru
        new_state[name] = status

        # skip first run
        if last_status is None:
            continue

        # detect change
        if status != last_status:
            if status == "running":
                alerts.append(f"✅ {name} : RUNNING KEMBALI")
            elif status == "down":
                alerts.append(f"⚠️ {name} : ❌ DOWN")

    return alerts, new_state
