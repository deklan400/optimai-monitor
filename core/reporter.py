def generate_report(current_data, last_rewards):
    report_lines = []
    total_diff = 0
    total_all = 0.0

    report_lines.append("🔥 OPTIMAI REPORT (3 JAM)\n")

    for item in current_data:
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

        total_diff += diff
        total_all += reward_val

        icon = "✅" if status == "running" else "❌"

        report_lines.append(f"{name} : {icon} | +{int(diff)}")

    report_lines.append("\n------------------------")
    report_lines.append(f"💰 Total 3 Jam : {int(total_diff)}")
    report_lines.append(f"💰 Total All   : {int(total_all)}")

    return "\n".join(report_lines)
