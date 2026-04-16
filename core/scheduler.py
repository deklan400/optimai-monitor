import time
from core.monitor import check_all_vps
from core.tracker import load_state, save_state, load_rewards, save_rewards
from core.alert import check_status_change
from core.reporter import generate_report
from services.telegram_bot import send_message
from utils.logger import log


CHECK_INTERVAL = 1800      # 30 menit
REPORT_INTERVAL = 10800    # 3 jam


def run(vps_list):
    last_report_time = time.time()

    while True:
        log("Checking VPS...")

        current_data = check_all_vps(vps_list)

        # load data lama
        last_state = load_state()
        last_rewards = load_rewards()

        # cek alert
        alerts, new_state = check_status_change(current_data, last_state)

        for alert in alerts:
            log(alert)
            send_message(alert)

        # simpan state
        save_state(new_state)

        # simpan reward terbaru
        new_rewards = {}
        for item in current_data:
            if item["reward"] is not None:
                new_rewards[item["host"]] = item["reward"]

        save_rewards(new_rewards)

        # cek apakah sudah 3 jam
        now = time.time()
        if now - last_report_time >= REPORT_INTERVAL:
            report = generate_report(current_data, last_rewards)
            log("Sending report...")
            send_message(report)

            last_report_time = now

        log("Sleep 30 menit...\n")
        time.sleep(CHECK_INTERVAL)
