import re

from services.ssh_client import run_ssh

MENU_INSTALL_NODE = "📦 Install Node"
MENU_CHECK_INSTALL = "🔍 Cek Install Node"
MENU_INSTALL_NOW = "🚀 Install Sekarang"
MENU_LATER = "⏳ Nanti Saja"


def _natural_key(value):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value or "")]


def get_node_install_status(host):
    command = r'''
printf 'cli=%s\n' "$(command -v optimai-cli 2>/dev/null || true)"
printf 'optimai=%s\n' "$(systemctl is-active optimai 2>/dev/null || true)"
printf 'docker=%s\n' "$(systemctl is-active docker 2>/dev/null || true)"
printf 'auth=%s\n' "$([ -d /root/.optimai ] && echo yes || echo no)"
'''
    output = run_ssh(host, command, timeout=25)
    if output is None:
        return {"ssh": False, "installed": False, "running": False, "reason": "SSH gagal"}

    info = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            info[key.strip()] = value.strip()

    installed = bool(info.get("cli"))
    running = info.get("optimai") == "active"
    docker = info.get("docker") or "unknown"
    auth = info.get("auth") or "unknown"

    if running:
        reason = "Node running"
    elif not installed:
        reason = "optimai-cli belum terinstall"
    elif docker != "active":
        reason = f"Docker {docker}"
    else:
        reason = f"Service optimai {info.get('optimai') or 'unknown'}"

    return {
        "ssh": True,
        "installed": installed,
        "running": running,
        "docker": docker,
        "auth": auth,
        "reason": reason,
    }


def install_status_report(vps_dict):
    if not vps_dict:
        return "Belum ada VPS terdaftar."

    lines = ["📦 STATUS INSTALL OPTIMAI NODE\n"]
    need_install = []
    for name, host in sorted(vps_dict.items(), key=lambda item: _natural_key(item[0])):
        status = get_node_install_status(host)
        if not status["ssh"]:
            icon = "❌"
        elif status["running"]:
            icon = "✅"
        elif status["installed"]:
            icon = "⚠️"
        else:
            icon = "📦"
            need_install.append(name)
        lines.append(f"{icon} {name} — {status['reason']}")

    if need_install:
        lines.append("\n⚠️ Ada VPS yang belum install OptimAI.")
        lines.append("Klik 🚀 Install Sekarang untuk buka dashboard install aman.")
    return "\n".join(lines)


def patch_telegram_bot(bot_module):
    old_keyboard = bot_module._main_keyboard
    old_handle_menu = bot_module._handle_menu
    old_stateful = bot_module._handle_stateful_message

    def main_keyboard():
        rows = old_keyboard()
        if not any(any(btn.get("text") == MENU_INSTALL_NODE for btn in row) for row in rows):
            rows.insert(4, [{"text": MENU_INSTALL_NODE}, {"text": MENU_CHECK_INSTALL}])
        return rows

    def send_install_menu(chat_id):
        vps_dict = bot_module.load_vps()
        report = install_status_report(vps_dict)
        rows = [[{"text": MENU_INSTALL_NOW}, {"text": MENU_LATER}], [{"text": MENU_CHECK_INSTALL}], [{"text": bot_module.MENU_CANCEL}]]
        bot_module.USER_STATE[str(chat_id)] = {"step": "install_node_menu"}
        bot_module._send_with_keyboard(chat_id, report, rows)

    def handle_stateful(chat_id, text):
        key = str(chat_id)
        state = bot_module.USER_STATE.get(key)
        if state and state.get("step") == "install_node_menu":
            if text == MENU_CHECK_INSTALL:
                send_install_menu(chat_id)
                return True
            if text == MENU_LATER or text == bot_module.MENU_CANCEL:
                bot_module.USER_STATE.pop(key, None)
                bot_module._send_with_keyboard(chat_id, "Oke bro, install node ditunda.", bot_module._main_keyboard())
                return True
            if text == MENU_INSTALL_NOW:
                bot_module.USER_STATE.pop(key, None)
                if bot_module.DASHBOARD_URL:
                    msg = (
                        "🚀 INSTALL NODE\n\n"
                        "Untuk keamanan, password OptimAI jangan lewat Telegram.\n"
                        "Buka dashboard lalu masuk menu Install Node.\n\n"
                        f"Link: {bot_module.DASHBOARD_URL}\n\n"
                        "Kalau menu Install Node belum muncul, kita patch dashboard setelah ini."
                    )
                else:
                    msg = (
                        "🚀 INSTALL NODE\n\n"
                        "DASHBOARD_URL belum diset di .env.\n"
                        "Password OptimAI jangan dikirim lewat Telegram."
                    )
                bot_module._send_with_keyboard(chat_id, msg, bot_module._main_keyboard())
                return True
        return old_stateful(chat_id, text)

    def handle_menu(chat_id, text):
        if text in (MENU_INSTALL_NODE, MENU_CHECK_INSTALL):
            send_install_menu(chat_id)
            return
        return old_handle_menu(chat_id, text)

    bot_module._main_keyboard = main_keyboard
    bot_module._handle_stateful_message = handle_stateful
    bot_module._handle_menu = handle_menu

    old_add_vps = bot_module.add_vps

    def add_vps_and_check(name, host):
        result = old_add_vps(name, host)
        try:
            status = get_node_install_status(host)
            if status.get("ssh") and not status.get("running"):
                bot_module.send_message(
                    f"⚠️ {name}: OptimAI node belum jalan.\n"
                    f"Penyebab: {status.get('reason')}\n\n"
                    f"Buka menu {MENU_INSTALL_NODE} untuk lanjut."
                )
        except Exception:
            pass
        return result

    bot_module.add_vps = add_vps_and_check
