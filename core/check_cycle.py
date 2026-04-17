import threading

from core.alert import check_status_change
from core.monitor import check_all_vps
from core.reporter import generate_report
from core.tracker import load_rewards, load_state, save_rewards, save_state

_CHECK_LOCK = threading.Lock()


def run_check_cycle(vps_dict):
    with _CHECK_LOCK:
        current_data = check_all_vps(vps_dict)

        last_state = load_state()
        last_rewards = load_rewards()

        alerts, new_state = check_status_change(current_data, last_state)
        save_state(new_state)

        new_rewards = {}
        for item in current_data:
            if item["reward"] is not None:
                new_rewards[item["name"]] = item["reward"]
        save_rewards(new_rewards)

        report = generate_report(current_data, last_rewards)
        return alerts, report
