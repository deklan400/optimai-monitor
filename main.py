from core.scheduler import run
from config import VPS_LIST
from utils.logger import log


def main():
    log("=== OPTIMAI MONITOR STARTED ===")

    try:
        run(VPS_LIST)

    except KeyboardInterrupt:
        log("Stopped by user")

    except Exception as e:
        log(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
