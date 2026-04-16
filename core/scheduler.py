import time

from core.monitor import check_all_vps
from core.tracker import load_state, save_state, load_rewards, save_rewards
from core.alert import check_status_change
from core.reporter import generate_report
from services.telegram_bot import send_message
from utils.logger import log
from config import CHECK_INTERVAL, REPORT_INTERVAL


def run(vps_dict):
    last_report_time = 0

    while True:
        log("=== CHECK VPS ===")

        # ambil data VPS
        current_data = check_all_vps(vps_dict)

        # load data lama
        last_state = load_state()
        last_rewards = load_rewards()

        # ======================
        # ALERT SYSTEM
        # ======================
        alerts, new_state = check_status_change(current_data, last_state)

        for alert in alerts:
            log(alert)
            send_message(alert)

        # simpan state
        save_state(new_state)

        # ======================
        # SAVE REWARD
        # ======================
        new_rewards = {}

        for item in current_data:
            name = item["name"]
            reward = item["reward"]

            if reward is not None:
                new_rewards[name] = reward

        save_rewards(new_rewards)

        # ======================
        # REPORT SYSTEM
        # ======================
        now = time.time()

        if now - last_report_time >= REPORT_INTERVAL:
            report = generate_report(current_data, last_rewards)

            log("Sending report...")
            send_message(report)

            last_report_time = now

        log("Sleep 30 menit...\n")
        time.sleep(CHECK_INTERVAL)
