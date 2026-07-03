import threading

from core.alert import check_status_change
from core.monitor import check_all_vps
from core.reporter import generate_manual_report, generate_report, get_account_reward
from core.tracker import (
    load_reward_snapshot,
    load_state,
    save_reward_snapshot,
    save_state,
)

_CHECK_LOCK = threading.Lock()


def run_check_cycle(vps_dict, report_title="🔥 OPTIMAI REPORT (3 JAM)", report_type="status"):
    with _CHECK_LOCK:
        current_data = check_all_vps(vps_dict)

        last_state = load_state()
        alerts, new_state = check_status_change(current_data, last_state)
        save_state(new_state)

        if report_type == "baseline":
            current_total, source_node = get_account_reward(current_data)
            if current_total is not None:
                save_reward_snapshot(current_total, source_node)
            report = None
        elif report_type == "manual":
            report = generate_manual_report(current_data, report_title=report_title)
        elif report_type == "scheduled":
            last_snapshot = load_reward_snapshot()
            report = generate_report(current_data, last_snapshot, report_title=report_title)
            current_total, source_node = get_account_reward(current_data)
            if current_total is not None:
                save_reward_snapshot(current_total, source_node)
        else:
            report = None

        return alerts, report
