from core.check_cycle import current_local_date, run_check_cycle
from core.history import get_recent_days, get_week_summary
from core.history_reports import (
    generate_daily_history_report,
    generate_weekly_history_report,
)


def build_ranking_report(vps_dict):
    _, report = run_check_cycle(vps_dict, report_type="ranking")
    return report


def build_detail_report(name, host):
    _, report = run_check_cycle({name: host}, report_type="detail")
    return report


def build_daily_history_report():
    return generate_daily_history_report(get_recent_days(limit=7))


def build_weekly_history_report():
    summary = get_week_summary(end_date=current_local_date(), days=7)
    return generate_weekly_history_report(summary)
