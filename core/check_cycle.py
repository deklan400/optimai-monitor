import threading
from datetime import datetime, time as dt_time, timedelta, timezone
from zoneinfo import ZoneInfo

from config import REPORT_TIMEZONE
from core.alert import check_status_change
from core.history import save_daily_snapshot
from core.monitor import check_all_vps
from core.ranking import generate_detail_report, generate_ranking_report
from core.reporter import (
    generate_daily_report,
    generate_manual_report,
    generate_report,
    get_account_reward,
)
from core.tracker import (
    load_reward_snapshot,
    load_state,
    save_reward_snapshot,
    save_state,
)

_CHECK_LOCK = threading.Lock()
_REPORT_TZ = ZoneInfo(REPORT_TIMEZONE)


def current_local_date():
    return datetime.now(_REPORT_TZ).date()


def day_window_utc(target_date=None):
    if target_date is None:
        target_date = current_local_date()

    start_local = datetime.combine(target_date, dt_time.min, tzinfo=_REPORT_TZ)
    end_local = start_local + timedelta(days=1)

    start_utc = start_local.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    end_utc = end_local.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return start_utc, end_utc


def run_check_cycle(
    vps_dict,
    report_title="🔥 OPTIMAI REPORT (3 JAM)",
    report_type="status",
    metrics_since=None,
    metrics_until=None,
    snapshot_date=None,
):
    with _CHECK_LOCK:
        metric_types = {"manual", "scheduled", "daily", "ranking", "detail"}
        reward_types = {"baseline", "manual", "scheduled", "daily"}
        needs_metrics = report_type in metric_types
        needs_reward = report_type in reward_types
        include_details = report_type == "detail"

        if needs_metrics and not metrics_since:
            metrics_since, _ = day_window_utc()

        current_data = check_all_vps(
            vps_dict,
            include_reward=needs_reward,
            metrics_since=metrics_since if needs_metrics else None,
            metrics_until=metrics_until if needs_metrics else None,
            include_details=include_details,
        )

        if report_type == "detail":
            alerts = []
        else:
            last_state = load_state()
            alerts, new_state = check_status_change(current_data, last_state)
            save_state(new_state)

        current_total, source_node = get_account_reward(current_data)

        if needs_metrics:
            if snapshot_date is not None:
                day_key = str(snapshot_date)
            elif report_type == "daily":
                day_key = str(current_local_date() - timedelta(days=1))
            else:
                day_key = str(current_local_date())
            save_daily_snapshot(day_key, current_data, current_total, source_node)

        if report_type == "baseline":
            if current_total is not None:
                save_reward_snapshot(current_total, source_node)
            report = None

        elif report_type == "manual":
            report = generate_manual_report(current_data, report_title=report_title)

        elif report_type == "scheduled":
            last_snapshot = load_reward_snapshot()
            report = generate_report(current_data, last_snapshot, report_title=report_title)
            if current_total is not None:
                save_reward_snapshot(current_total, source_node)

        elif report_type == "daily":
            report = generate_daily_report(current_data, report_title=report_title)

        elif report_type == "ranking":
            report = generate_ranking_report(current_data)

        elif report_type == "detail":
            report = generate_detail_report(current_data[0]) if current_data else "VPS tidak ditemukan."

        else:
            report = None

        return alerts, report
