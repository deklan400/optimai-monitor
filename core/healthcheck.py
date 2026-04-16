import os

REQUIRED_FILES = [
    "data/state.json",
    "data/rewards.json"
]


def check_files():
    for file in REQUIRED_FILES:
        if not os.path.exists(file):
            with open(file, "w") as f:
                f.write("{}")


def check_env():
    from config import BOT_TOKEN, CHAT_ID

    if not BOT_TOKEN or not CHAT_ID:
        print("[ERROR] BOT_TOKEN / CHAT_ID belum di set di .env")
        return False

    return True


def run_healthcheck():
    print("[HEALTHCHECK] Checking system...")

    check_files()

    if not check_env():
        return False

    print("[HEALTHCHECK] OK")
    return True
