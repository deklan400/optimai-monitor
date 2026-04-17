import time

from core.check_cycle import run_check_cycle
from services.telegram_bot import send_message
from utils.logger import log
from config import CHECK_INTERVAL, REPORT_INTERVAL


def run(vps_source):
    # Mulai hitung interval dari waktu bot dijalankan, agar report 3 jam
    # tidak langsung terkirim saat startup/restart.
    last_report_time = time.time()

    while True:
        log("=== CHECK VPS ===")

        if callable(vps_source):
            vps_dict = vps_source()
        else:
            vps_dict = vps_source

        if not vps_dict:
            log("[WARNING] Daftar VPS kosong, skip check")
            time.sleep(CHECK_INTERVAL)
            continue

        # Jalankan satu siklus check terproteksi lock agar tidak tabrakan
        # dengan check manual dari Telegram.
        alerts, report = run_check_cycle(vps_dict)

        for alert in alerts:
            log(alert)
            send_message(alert)

        # ======================
        # REPORT SYSTEM
        # ======================
        now = time.time()

        if now - last_report_time >= REPORT_INTERVAL:
            log("Sending report...")
            send_message(report)

            last_report_time = now

        sleep_minutes = CHECK_INTERVAL // 60
        if sleep_minutes > 0:
            log(f"Sleep {sleep_minutes} menit...\n")
        else:
            log(f"Sleep {CHECK_INTERVAL} detik...\n")
        time.sleep(CHECK_INTERVAL)
