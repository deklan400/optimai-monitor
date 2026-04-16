def generate_report(current_data, last_rewards):
    report_lines = []
    total_diff = 0
    total_all = 0

    report_lines.append("🔥 OPTIMAI REPORT (3 JAM)\n")

    for item in current_data:
        name = item["name"]
        status = item["status"]
        reward = item["reward"]

        if reward is None:
            diff = 0
        else:
            last = last_rewards.get(name, reward)

            if reward < last:
                diff = 0
            else:
                diff = int(reward - last)

        total_diff += diff
        total_all += int(reward) if reward else 0

        icon = "✅" if status == "running" else "❌"

        report_lines.append(f"{name} : {icon} | +{diff}")

    report_lines.append("\n------------------------")
    report_lines.append(f"💰 Total 3 Jam : {total_diff}")
    report_lines.append(f"💰 Total All   : {total_all}")

    return "\n".join(report_lines)
