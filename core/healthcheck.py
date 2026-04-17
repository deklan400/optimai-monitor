import os
from dotenv import load_dotenv

REQUIRED_FILES = [
    "data/state.json",
    "data/rewards.json",
    "data/vps_list.json",
    "data/history.json",
    "data/logs.txt",
]


def check_files():
    os.makedirs("data", exist_ok=True)

    for file in REQUIRED_FILES:
        if not os.path.exists(file):
            with open(file, "w") as f:
                if file.endswith(".json"):
                    f.write("{}")
                else:
                    f.write("")


def check_env():
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not bot_token or not chat_id:
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
