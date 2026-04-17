import requests
import os
import re
import time
from dotenv import load_dotenv
from core.vps_store import add_vps, delete_vps, load_vps

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ADMIN_CHAT_ID = str(CHAT_ID) if CHAT_ID else None
USER_STATE = {}

MENU_LIST = "📋 List VPS"
MENU_ADD = "➕ Tambah VPS"
MENU_DELETE = "❌ Hapus VPS"
MENU_CANCEL = "🔙 Batal"


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


def _post(url, payload):
    try:
        return requests.post(url, json=payload, timeout=30)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return None


def _send_with_keyboard(chat_id, text, keyboard_rows):
    if not BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": text,
        "reply_markup": {
            "keyboard": keyboard_rows,
            "resize_keyboard": True,
            "one_time_keyboard": False,
        },
    }
    _post(url, payload)


def send_menu(chat_id):
    keyboard = [
        [{"text": MENU_LIST}, {"text": MENU_ADD}],
        [{"text": MENU_DELETE}],
    ]
    _send_with_keyboard(chat_id, "Pilih menu:", keyboard)


def _is_valid_name(name):
    return bool(re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", name))


def _is_valid_host(host):
    if "@" not in host:
        return False
    user, target = host.split("@", 1)
    if not user or not target:
        return False
    return True


def _render_vps_list():
    vps_dict = load_vps()
    if not vps_dict:
        return "Belum ada VPS terdaftar."

    lines = ["📋 Daftar VPS:"]
    for name, host in sorted(vps_dict.items()):
        lines.append(f"- {name}: {host}")
    return "\n".join(lines)


def _start_add_flow(chat_id):
    USER_STATE[str(chat_id)] = {"step": "await_name"}
    keyboard = [[{"text": MENU_CANCEL}]]
    _send_with_keyboard(chat_id, "Masukkan nama VPS (contoh: vps3):", keyboard)


def _start_delete_flow(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        send_message("Belum ada VPS untuk dihapus.")
        send_menu(chat_id)
        return

    USER_STATE[str(chat_id)] = {"step": "await_delete_name"}
    rows = [[{"text": name}] for name in sorted(vps_dict.keys())]
    rows.append([{"text": MENU_CANCEL}])
    _send_with_keyboard(chat_id, "Pilih nama VPS yang mau dihapus:", rows)


def _handle_stateful_message(chat_id, text):
    key = str(chat_id)
    state = USER_STATE.get(key)
    if not state:
        return False

    if text == MENU_CANCEL:
        USER_STATE.pop(key, None)
        _send_with_keyboard(chat_id, "Aksi dibatalkan.", [[{"text": MENU_LIST}, {"text": MENU_ADD}], [{"text": MENU_DELETE}]])
        return True

    if state["step"] == "await_name":
        name = text.strip()
        if not _is_valid_name(name):
            _send_with_keyboard(chat_id, "Nama tidak valid. Gunakan huruf/angka/-/_ (maks 32).", [[{"text": MENU_CANCEL}]])
            return True

        vps_dict = load_vps()
        if name in vps_dict:
            _send_with_keyboard(chat_id, "Nama sudah dipakai. Masukkan nama lain.", [[{"text": MENU_CANCEL}]])
            return True

        USER_STATE[key] = {"step": "await_host", "name": name}
        _send_with_keyboard(chat_id, f"Masukkan host untuk {name} (format user@ip):", [[{"text": MENU_CANCEL}]])
        return True

    if state["step"] == "await_host":
        host = text.strip()
        if not _is_valid_host(host):
            _send_with_keyboard(chat_id, "Format host tidak valid. Gunakan user@ip", [[{"text": MENU_CANCEL}]])
            return True

        name = state["name"]
        add_vps(name, host)
        USER_STATE.pop(key, None)
        _send_with_keyboard(chat_id, f"✅ VPS ditambahkan:\n- {name}: {host}", [[{"text": MENU_LIST}, {"text": MENU_ADD}], [{"text": MENU_DELETE}]])
        return True

    if state["step"] == "await_delete_name":
        name = text.strip()
        deleted = delete_vps(name)
        USER_STATE.pop(key, None)
        if deleted:
            _send_with_keyboard(chat_id, f"✅ VPS dihapus: {name}", [[{"text": MENU_LIST}, {"text": MENU_ADD}], [{"text": MENU_DELETE}]])
        else:
            _send_with_keyboard(chat_id, "Nama VPS tidak ditemukan.", [[{"text": MENU_LIST}, {"text": MENU_ADD}], [{"text": MENU_DELETE}]])
        return True

    return False


def _handle_menu(chat_id, text):
    if text == MENU_LIST:
        _send_with_keyboard(chat_id, _render_vps_list(), [[{"text": MENU_LIST}, {"text": MENU_ADD}], [{"text": MENU_DELETE}]])
        return
    if text == MENU_ADD:
        _start_add_flow(chat_id)
        return
    if text == MENU_DELETE:
        _start_delete_flow(chat_id)
        return

    _send_with_keyboard(chat_id, "Menu tidak dikenali. Pilih tombol yang tersedia.", [[{"text": MENU_LIST}, {"text": MENU_ADD}], [{"text": MENU_DELETE}]])


def _fetch_updates(offset):
    if not BOT_TOKEN:
        return []

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    payload = {"timeout": 25, "offset": offset}
    res = _post(url, payload)

    if not res or res.status_code != 200:
        return []

    try:
        body = res.json()
    except Exception:
        return []

    if not body.get("ok"):
        return []
    return body.get("result", [])


def start_menu_listener():
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print("[TELEGRAM] Listener tidak aktif. Cek BOT_TOKEN/CHAT_ID.")
        return

    print("[TELEGRAM] Menu listener aktif.")
    send_menu(ADMIN_CHAT_ID)

    offset = 0
    while True:
        updates = _fetch_updates(offset)
        if not updates:
            time.sleep(1)
            continue

        for item in updates:
            offset = item["update_id"] + 1
            msg = item.get("message", {})
            if not msg:
                continue

            chat = msg.get("chat", {})
            chat_id = str(chat.get("id", ""))
            text = msg.get("text", "")
            if not text:
                continue

            if chat_id != ADMIN_CHAT_ID:
                _send_with_keyboard(chat_id, "Akses ditolak.", [[{"text": MENU_LIST}]])
                continue

            if text in ("/start", "menu", "Menu"):
                USER_STATE.pop(chat_id, None)
                send_menu(chat_id)
                continue

            if _handle_stateful_message(chat_id, text):
                continue

            _handle_menu(chat_id, text)
