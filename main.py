from core.scheduler import run
from core.healthcheck import run_healthcheck
from core.vps_store import load_vps
from services.telegram_bot import start_menu_listener
from utils.logger import log
import threading

try:
    import services.telegram_bot as telegram_bot
    from services.node_install_advisor import patch_telegram_bot
    patch_telegram_bot(telegram_bot)
except Exception as exc:
    print(f"[WARN] node install advisor disabled: {exc}")


def main():
    log("=== OPTIMAI MONITOR STARTED ===")

    try:
        if not run_healthcheck():
            log("[ERROR] Healthcheck failed")
            return

        listener = threading.Thread(target=start_menu_listener, daemon=True)
        listener.start()

        run(load_vps)

    except KeyboardInterrupt:
        log("Stopped by user")

    except Exception as e:
        log(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
