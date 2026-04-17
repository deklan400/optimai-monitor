def generate_report(current_data, last_rewards):
    report_lines = []
    total_diff = 0
    total_all = 0.0
    total_source_node = "-"

    report_lines.append("🔥 OPTIMAI REPORT (3 JAM)\n")

    sorted_data = sorted(current_data, key=lambda item: item["name"].lower())

    for item in sorted_data:
        name = item["name"]
        status = item["status"]
        reward = item["reward"]

        if reward is None:
            diff = 0
            reward_val = 0
        else:
            last = last_rewards.get(name)

            if last is None:
                diff = 0
            elif reward < last:
                diff = 0
            else:
                diff = reward - last

            reward_val = reward

        display_diff = int(diff)
        total_diff += display_diff

        icon = "✅" if status == "running" else "❌"

        report_lines.append(f"{name} : {icon} | +{display_diff}")

        # Total all diambil dari satu node sumber prioritas pertama yang running.
        if total_source_node == "-" and status == "running" and reward is not None:
            total_source_node = name
            total_all = reward_val

    report_lines.append("")
    report_lines.append("------------------------")
    report_lines.append(f"💰 Total 3 Jam : {int(total_diff)}")
    report_lines.append(f"💰 Total All   : {int(total_all)}")
    report_lines.append(f"📍 Sumber Total: {total_source_node}")

    return "\n".join(report_lines)
