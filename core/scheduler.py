import time
from datetime import timedelta

from config import CHECK_INTERVAL, REPORT_INTERVAL
from core.check_cycle import current_local_date, day_window_utc, run_check_cycle
from services.telegram_bot import send_message
from utils.logger import log


def _resolve_vps(vps_source):
    return vps_source() if callable(vps_source) else vps_source


def _send_alerts(alerts):
    for alert in alerts:
        log(alert)
        send_message(alert)


def run(vps_source):
    last_report_time = time.time()
    last_local_date = current_local_date()
    baseline_ready = False

    while True:
        log("=== CHECK VPS ===")
        vps_dict = _resolve_vps(vps_source)

        if not vps_dict:
            log("[WARNING] Daftar VPS kosong, skip check")
            time.sleep(CHECK_INTERVAL)
            continue

        if not baseline_ready:
            alerts, _ = run_check_cycle(vps_dict, report_type="baseline")
            baseline_ready = True
            log("Reward baseline initialized")
        else:
            alerts, _ = run_check_cycle(vps_dict, report_type="status")

        _send_alerts(alerts)

        current_date = current_local_date()
        if current_date != last_local_date:
            report_date = current_date - timedelta(days=1)
            metrics_since, metrics_until = day_window_utc(report_date)
            report_title = f"📊 OPTIMAI REPORT HARIAN ({report_date.strftime('%d-%m-%Y')})"
            daily_alerts, daily_report = run_check_cycle(
                vps_dict,
                report_title=report_title,
                report_type="daily",
                metrics_since=metrics_since,
                metrics_until=metrics_until,
            )
            _send_alerts(daily_alerts)
            if daily_report:
                send_message(daily_report)
            last_local_date = current_date

        now = time.time()
        if now - last_report_time >= REPORT_INTERVAL:
            log("Sending 3-hour report...")
            report_alerts, report = run_check_cycle(vps_dict, report_type="scheduled")
            _send_alerts(report_alerts)
            if report:
                send_message(report)
            last_report_time = now

        sleep_minutes = CHECK_INTERVAL // 60
        if sleep_minutes > 0:
            log(f"Sleep {sleep_minutes} menit...\n")
        else:
            log(f"Sleep {CHECK_INTERVAL} detik...\n")
        time.sleep(CHECK_INTERVAL)
