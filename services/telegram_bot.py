import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("[TELEGRAM] Token / Chat ID belum diset")
        return

    # limit message
    if len(text) > 4000:
        text = text[:4000] + "\n...(cut)"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        res = requests.post(url, json=payload, timeout=10)

        if res.status_code != 200:
            print(f"[TELEGRAM ERROR] {res.text}")

    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
