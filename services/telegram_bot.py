import os
import re
import time

import requests
from dotenv import load_dotenv

from core.check_cycle import run_check_cycle
from core.vps_store import add_vps, delete_vps, load_vps, update_vps
from services.feature_handlers import (
    build_daily_history_report,
    build_detail_report,
    build_ranking_report,
    build_weekly_history_report,
)
from services.ssh_bootstrap import setup_ssh_key_with_password
from services.ssh_client import test_ssh_connection

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ADMIN_CHAT_ID = str(CHAT_ID) if CHAT_ID else None
USER_STATE = {}

MENU_LIST = "📋 List VPS"
MENU_ADD = "➕ Tambah VPS"
MENU_DELETE = "❌ Hapus VPS"
MENU_EDIT = "✏️ Edit VPS"
MENU_TEST_SSH = "🔍 Test SSH"
MENU_CHECK_NOW = "⚡ Check Manual"
MENU_DETAIL = "🔎 Detail VPS"
MENU_RANKING = "🏆 Ranking Harian"
MENU_HISTORY_DAILY = "📅 Riwayat Harian"
MENU_HISTORY_WEEKLY = "📈 Riwayat Mingguan"
MENU_CANCEL = "🔙 Batal"
MENU_SKIP_PASSWORD = "⏭️ Lewati Password"
MENU_TEST_ALL = "🔍 Test Semua VPS"


def _natural_key(value):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
    ]


def _sorted_vps_names(vps_dict):
    return sorted(vps_dict.keys(), key=_natural_key)


def _sorted_vps_items(vps_dict):
    return sorted(vps_dict.items(), key=lambda item: _natural_key(item[0]))


def _main_keyboard():
    return [
        [{"text": MENU_LIST}, {"text": MENU_ADD}],
        [{"text": MENU_EDIT}, {"text": MENU_DELETE}],
        [{"text": MENU_TEST_SSH}, {"text": MENU_CHECK_NOW}],
        [{"text": MENU_DETAIL}, {"text": MENU_RANKING}],
        [{"text": MENU_HISTORY_DAILY}, {"text": MENU_HISTORY_WEEKLY}],
    ]


def send_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("[TELEGRAM] Token / Chat ID belum diset")
        return

    if len(text) > 4000:
        text = text[:4000] + "\n...(cut)"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}

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
    _send_with_keyboard(chat_id, "Pilih menu:", _main_keyboard())


def _is_valid_name(name):
    return bool(re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", name))


def _is_valid_host(host):
    if "@" not in host:
        return False
    user, target = host.split("@", 1)
    return bool(user and target)


def _render_vps_list():
    vps_dict = load_vps()
    if not vps_dict:
        return "Belum ada VPS terdaftar."

    lines = ["📋 Daftar VPS:"]
    for name, host in _sorted_vps_items(vps_dict):
        lines.append(f"- {name}: {host}")
    return "\n".join(lines)


def _run_manual_check(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        _send_with_keyboard(chat_id, "Daftar VPS masih kosong.", _main_keyboard())
        return

    _send_with_keyboard(chat_id, "⏳ Menjalankan check manual...", _main_keyboard())
    alerts, report = run_check_cycle(
        vps_dict,
        report_title="⚡ OPTIMAI CHECK MANUAL",
        report_type="manual",
    )
    for alert in alerts:
        send_message(alert)
    _send_with_keyboard(chat_id, report, _main_keyboard())


def _run_ranking(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        _send_with_keyboard(chat_id, "Daftar VPS masih kosong.", _main_keyboard())
        return

    _send_with_keyboard(chat_id, "⏳ Menghitung ranking harian...", _main_keyboard())
    report = build_ranking_report(vps_dict)
    _send_with_keyboard(chat_id, report, _main_keyboard())


def _run_daily_history(chat_id):
    _send_with_keyboard(chat_id, build_daily_history_report(), _main_keyboard())


def _run_weekly_history(chat_id):
    _send_with_keyboard(chat_id, build_weekly_history_report(), _main_keyboard())


def _start_detail_flow(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        _send_with_keyboard(chat_id, "Daftar VPS masih kosong.", _main_keyboard())
        return

    USER_STATE[str(chat_id)] = {"step": "await_detail_name"}
    rows = [[{"text": name}] for name in _sorted_vps_names(vps_dict)]
    rows.append([{"text": MENU_CANCEL}])
    _send_with_keyboard(chat_id, "Pilih VPS untuk melihat detail:", rows)


def _start_add_flow(chat_id):
    USER_STATE[str(chat_id)] = {"step": "await_name"}
    _send_with_keyboard(chat_id, "Masukkan nama VPS (contoh: vps3):", [[{"text": MENU_CANCEL}]])


def _start_delete_flow(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        send_message("Belum ada VPS untuk dihapus.")
        send_menu(chat_id)
        return

    USER_STATE[str(chat_id)] = {"step": "await_delete_name"}
    rows = [[{"text": name}] for name in _sorted_vps_names(vps_dict)]
    rows.append([{"text": MENU_CANCEL}])
    _send_with_keyboard(chat_id, "Pilih nama VPS yang mau dihapus:", rows)


def _start_edit_flow(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        _send_with_keyboard(chat_id, "Belum ada VPS untuk diedit.", _main_keyboard())
        return

    USER_STATE[str(chat_id)] = {"step": "await_edit_name"}
    rows = [[{"text": name}] for name in _sorted_vps_names(vps_dict)]
    rows.append([{"text": MENU_CANCEL}])
    _send_with_keyboard(chat_id, "Pilih nama VPS yang mau diedit:", rows)


def _run_test_all(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        _send_with_keyboard(chat_id, "Daftar VPS masih kosong.", _main_keyboard())
        return

    _send_with_keyboard(chat_id, "⏳ Menjalankan test SSH semua VPS...", _main_keyboard())
    lines = ["🔍 HASIL TEST SSH (SEMUA VPS)\n"]
    for name, host in _sorted_vps_items(vps_dict):
        ok, detail = test_ssh_connection(host)
        if ok:
            lines.append(f"✅ {name} ({host}) : OK")
        else:
            lines.append(f"❌ {name} ({host}) : {detail}")
    _send_with_keyboard(chat_id, "\n".join(lines), _main_keyboard())


def _start_test_ssh_flow(chat_id):
    vps_dict = load_vps()
    if not vps_dict:
        _send_with_keyboard(chat_id, "Daftar VPS masih kosong.", _main_keyboard())
        return

    USER_STATE[str(chat_id)] = {"step": "await_test_name"}
    rows = [[{"text": MENU_TEST_ALL}]]
    rows.extend([[{"text": name}] for name in _sorted_vps_names(vps_dict)])
    rows.append([{"text": MENU_CANCEL}])
    _send_with_keyboard(chat_id, "Pilih VPS untuk test SSH:", rows)


def _handle_stateful_message(chat_id, text):
    key = str(chat_id)
    state = USER_STATE.get(key)
    if not state:
        return False

    if text == MENU_CANCEL:
        USER_STATE.pop(key, None)
        _send_with_keyboard(chat_id, "Aksi dibatalkan.", _main_keyboard())
        return True

    if state["step"] == "await_detail_name":
        name = text.strip()
        vps_dict = load_vps()
        host = vps_dict.get(name)
        if not host:
            rows = [[{"text": n}] for n in _sorted_vps_names(vps_dict)]
            rows.append([{"text": MENU_CANCEL}])
            _send_with_keyboard(chat_id, "Nama VPS tidak ditemukan. Pilih dari tombol.", rows)
            return True

        USER_STATE.pop(key, None)
        _send_with_keyboard(chat_id, f"⏳ Mengambil detail {name}...", _main_keyboard())
        _send_with_keyboard(chat_id, build_detail_report(name, host), _main_keyboard())
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
        USER_STATE[key] = {"step": "await_password", "name": name, "host": host}
        _send_with_keyboard(
            chat_id,
            f"Masukkan password SSH untuk {host}.\nPassword hanya dipakai sekali untuk setup key.\nAtau klik tombol lewati jika key sudah terpasang.",
            [[{"text": MENU_SKIP_PASSWORD}], [{"text": MENU_CANCEL}]],
        )
        return True

    if state["step"] == "await_password":
        name = state["name"]
        host = state["host"]

        if text == MENU_SKIP_PASSWORD:
            add_vps(name, host)
            USER_STATE.pop(key, None)
            _send_with_keyboard(chat_id, f"✅ VPS ditambahkan (tanpa setup key):\n- {name}: {host}", _main_keyboard())
            return True

        password = text.strip()
        if not password:
            _send_with_keyboard(chat_id, "Password kosong. Masukkan password atau pilih lewati.", [[{"text": MENU_SKIP_PASSWORD}], [{"text": MENU_CANCEL}]])
            return True

        _send_with_keyboard(chat_id, f"Sedang setup SSH key ke {host}...", [[{"text": MENU_CANCEL}]])
        ok, detail = setup_ssh_key_with_password(host, password)
        if not ok:
            _send_with_keyboard(chat_id, f"❌ Gagal setup SSH key:\n{detail}\n\nCoba kirim password lagi atau klik lewati.", [[{"text": MENU_SKIP_PASSWORD}], [{"text": MENU_CANCEL}]])
            return True

        add_vps(name, host)
        USER_STATE.pop(key, None)
        _send_with_keyboard(chat_id, f"✅ VPS ditambahkan dan SSH key sukses:\n- {name}: {host}", _main_keyboard())
        return True

    if state["step"] == "await_edit_name":
        name = text.strip()
        vps_dict = load_vps()
        if name not in vps_dict:
            rows = [[{"text": n}] for n in _sorted_vps_names(vps_dict)] + [[{"text": MENU_CANCEL}]]
            _send_with_keyboard(chat_id, "Nama VPS tidak ditemukan. Pilih dari tombol.", rows)
            return True

        USER_STATE[key] = {"step": "await_edit_host", "name": name}
        _send_with_keyboard(chat_id, f"Masukkan host baru untuk {name} (format user@ip):", [[{"text": MENU_CANCEL}]])
        return True

    if state["step"] == "await_edit_host":
        host = text.strip()
        if not _is_valid_host(host):
            _send_with_keyboard(chat_id, "Format host tidak valid. Gunakan user@ip", [[{"text": MENU_CANCEL}]])
            return True

        name = state["name"]
        USER_STATE.pop(key, None)
        if update_vps(name, host):
            _send_with_keyboard(chat_id, f"✅ VPS diperbarui:\n- {name}: {host}", _main_keyboard())
        else:
            _send_with_keyboard(chat_id, "Nama VPS tidak ditemukan saat update.", _main_keyboard())
        return True

    if state["step"] == "await_delete_name":
        name = text.strip()
        deleted = delete_vps(name)
        USER_STATE.pop(key, None)
        message = f"✅ VPS dihapus: {name}" if deleted else "Nama VPS tidak ditemukan."
        _send_with_keyboard(chat_id, message, _main_keyboard())
        return True

    if state["step"] == "await_test_name":
        if text == MENU_TEST_ALL:
            USER_STATE.pop(key, None)
            _run_test_all(chat_id)
            return True

        name = text.strip()
        vps_dict = load_vps()
        host = vps_dict.get(name)
        if not host:
            rows = [[{"text": MENU_TEST_ALL}]] + [[{"text": n}] for n in _sorted_vps_names(vps_dict)] + [[{"text": MENU_CANCEL}]]
            _send_with_keyboard(chat_id, "Nama VPS tidak ditemukan. Pilih dari tombol.", rows)
            return True

        USER_STATE.pop(key, None)
        _send_with_keyboard(chat_id, f"⏳ Menjalankan test SSH untuk {name}...", _main_keyboard())
        ok, detail = test_ssh_connection(host)
        if ok:
            _send_with_keyboard(chat_id, f"✅ SSH OK\n- {name}: {host}", _main_keyboard())
        else:
            _send_with_keyboard(chat_id, f"❌ SSH FAIL\n- {name}: {host}\n- detail: {detail}", _main_keyboard())
        return True

    return False


def _handle_menu(chat_id, text):
    if text == MENU_LIST:
        _send_with_keyboard(chat_id, _render_vps_list(), _main_keyboard())
    elif text == MENU_ADD:
        _start_add_flow(chat_id)
    elif text == MENU_EDIT:
        _start_edit_flow(chat_id)
    elif text == MENU_DELETE:
        _start_delete_flow(chat_id)
    elif text == MENU_TEST_SSH:
        _start_test_ssh_flow(chat_id)
    elif text == MENU_CHECK_NOW:
        _run_manual_check(chat_id)
    elif text == MENU_DETAIL:
        _start_detail_flow(chat_id)
    elif text == MENU_RANKING:
        _run_ranking(chat_id)
    elif text == MENU_HISTORY_DAILY:
        _run_daily_history(chat_id)
    elif text == MENU_HISTORY_WEEKLY:
        _run_weekly_history(chat_id)
    else:
        _send_with_keyboard(chat_id, "Menu tidak dikenali. Pilih tombol yang tersedia.", _main_keyboard())


def _fetch_updates(offset):
    if not BOT_TOKEN:
        return []

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    res = _post(url, {"timeout": 25, "offset": offset})
    if not res or res.status_code != 200:
        return []

    try:
        body = res.json()
    except Exception:
        return []

    return body.get("result", []) if body.get("ok") else []


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

            chat_id = str(msg.get("chat", {}).get("id", ""))
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
