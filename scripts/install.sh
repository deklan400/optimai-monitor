#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

print_line() {
  echo "===================================="
}

ask_default() {
  local prompt="$1"
  local default_value="$2"
  local answer=""
  if [[ -n "${default_value}" ]]; then
    read -r -p "${prompt} [${default_value}]: " answer
    echo "${answer:-$default_value}"
  else
    read -r -p "${prompt}: " answer
    echo "${answer}"
  fi
}

random_secret() {
  if command -v sha256sum >/dev/null 2>&1; then
    date +%s%N | sha256sum | cut -c1-48
  else
    date +%s%N
  fi
}

public_ip() {
  local ip=""
  ip="$(curl -fsS --max-time 5 ifconfig.me 2>/dev/null || true)"
  if [[ -z "${ip}" ]]; then
    ip="IP-VPS-BARU"
  fi
  echo "${ip}"
}

print_line
echo " OPTIMAI MONITOR + DASHBOARD INSTALLER"
echo " Sekali jalan: bot Telegram + website dashboard"
print_line

if [[ "${EUID}" -ne 0 ]]; then
  echo "[INFO] Installer butuh sudo/root untuk apt dan systemd."
  echo "[INFO] Kalau gagal permission, jalankan: sudo bash scripts/install.sh"
fi

echo "[STEP] Update package index..."
sudo apt update -y

echo "[STEP] Install dependency sistem..."
sudo apt install -y python3 python3-venv python3-pip openssh-client screen sshpass curl git nano

echo "[STEP] Buat virtualenv..."
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

echo "[STEP] Install dependency Python..."
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[STEP] Setup folder data..."
mkdir -p data
[[ -f data/state.json ]] || echo "{}" > data/state.json
[[ -f data/rewards.json ]] || echo "{}" > data/rewards.json
[[ -f data/history.json ]] || echo '{"days": {}}' > data/history.json
[[ -f data/vps_list.json ]] || echo "{}" > data/vps_list.json
[[ -f data/logs.txt ]] || touch data/logs.txt
[[ -f data/daily_report_state.json ]] || echo "{}" > data/daily_report_state.json

EXISTING_BOT_TOKEN=""
EXISTING_CHAT_ID=""
EXISTING_DASHBOARD_URL=""
EXISTING_ALLOWED_IDS=""
EXISTING_SESSION_SECRET=""
EXISTING_TIMEZONE="Asia/Jakarta"
EXISTING_CHECK_INTERVAL="60"
EXISTING_REPORT_INTERVAL="10800"
EXISTING_DASHBOARD_PORT="8080"

if [[ -f .env ]]; then
  EXISTING_BOT_TOKEN="$(grep -E '^BOT_TOKEN=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_CHAT_ID="$(grep -E '^CHAT_ID=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_DASHBOARD_URL="$(grep -E '^DASHBOARD_URL=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_ALLOWED_IDS="$(grep -E '^DASHBOARD_ALLOWED_TELEGRAM_IDS=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_SESSION_SECRET="$(grep -E '^DASHBOARD_SESSION_SECRET=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_TIMEZONE="$(grep -E '^REPORT_TIMEZONE=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_CHECK_INTERVAL="$(grep -E '^CHECK_INTERVAL=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_REPORT_INTERVAL="$(grep -E '^REPORT_INTERVAL=' .env | tail -1 | cut -d= -f2- || true)"
  EXISTING_DASHBOARD_PORT="$(grep -E '^DASHBOARD_PORT=' .env | tail -1 | cut -d= -f2- || true)"
fi

EXISTING_TIMEZONE="${EXISTING_TIMEZONE:-Asia/Jakarta}"
EXISTING_CHECK_INTERVAL="${EXISTING_CHECK_INTERVAL:-60}"
EXISTING_REPORT_INTERVAL="${EXISTING_REPORT_INTERVAL:-10800}"
EXISTING_DASHBOARD_PORT="${EXISTING_DASHBOARD_PORT:-8080}"

print_line
echo " SET TELEGRAM + DASHBOARD CONFIG"
print_line
BOT_TOKEN="$(ask_default "Masukkan BOT_TOKEN" "${EXISTING_BOT_TOKEN}")"
CHAT_ID="$(ask_default "Masukkan CHAT_ID / Telegram ID admin" "${EXISTING_CHAT_ID}")"
DASHBOARD_PORT="$(ask_default "Dashboard port" "${EXISTING_DASHBOARD_PORT}")"

DEFAULT_DASHBOARD_URL="${EXISTING_DASHBOARD_URL}"
if [[ -z "${DEFAULT_DASHBOARD_URL}" ]]; then
  DEFAULT_DASHBOARD_URL="http://$(public_ip):${DASHBOARD_PORT}"
fi
DASHBOARD_URL="$(ask_default "DASHBOARD_URL" "${DEFAULT_DASHBOARD_URL}")"

DEFAULT_ALLOWED_IDS="${EXISTING_ALLOWED_IDS:-$CHAT_ID}"
DASHBOARD_ALLOWED_TELEGRAM_IDS="$(ask_default "Allowed Telegram IDs dashboard, pisah koma kalau banyak" "${DEFAULT_ALLOWED_IDS}")"
DASHBOARD_SESSION_SECRET="${EXISTING_SESSION_SECRET:-$(random_secret)}"
REPORT_TIMEZONE="$(ask_default "Timezone report" "${EXISTING_TIMEZONE}")"
CHECK_INTERVAL="$(ask_default "Check interval detik" "${EXISTING_CHECK_INTERVAL}")"
REPORT_INTERVAL="$(ask_default "Report interval detik" "${EXISTING_REPORT_INTERVAL}")"

if [[ -z "${BOT_TOKEN}" || -z "${CHAT_ID}" ]]; then
  echo "[ERROR] BOT_TOKEN dan CHAT_ID wajib diisi."
  exit 1
fi

if [[ -f .env ]]; then
  cp .env ".env.backup.$(date +%F-%H%M%S)"
fi

cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
CHAT_ID=${CHAT_ID}
REPORT_TIMEZONE=${REPORT_TIMEZONE}
CHECK_INTERVAL=${CHECK_INTERVAL}
REPORT_INTERVAL=${REPORT_INTERVAL}
DASHBOARD_PORT=${DASHBOARD_PORT}
DASHBOARD_URL=${DASHBOARD_URL}
DASHBOARD_ALLOWED_TELEGRAM_IDS=${DASHBOARD_ALLOWED_TELEGRAM_IDS}
DASHBOARD_SESSION_SECRET=${DASHBOARD_SESSION_SECRET}
DASHBOARD_TOKEN=${DASHBOARD_SESSION_SECRET}
EOF

echo "[OK] .env berhasil dibuat."

chmod +x scripts/setup_systemd.sh scripts/setup_dashboard_systemd.sh 2>/dev/null || true

print_line
echo "Pilih mode run:"
echo "1) Run bot langsung foreground"
echo "2) Run bot background screen"
echo "3) Install bot + dashboard systemd (recommended)"
echo "4) Install bot systemd saja"
echo "5) Install dashboard systemd saja"
read -r -p "Pilih [1/2/3/4/5] default 3: " MODE
MODE="${MODE:-3}"

if [[ "${MODE}" == "2" ]]; then
  echo "[STEP] Menjalankan bot di background via screen..."
  screen -dmS optimai-monitor bash -lc "cd '${PROJECT_DIR}' && source .venv/bin/activate && python main.py"
  echo "[OK] Bot berjalan di background."
  echo "Cek: screen -ls"
  echo "Attach: screen -r optimai-monitor"
elif [[ "${MODE}" == "3" ]]; then
  echo "[STEP] Setup bot systemd service..."
  sudo bash scripts/setup_systemd.sh
  echo "[STEP] Setup dashboard systemd service..."
  sudo DASHBOARD_PORT="${DASHBOARD_PORT}" bash scripts/setup_dashboard_systemd.sh
elif [[ "${MODE}" == "4" ]]; then
  echo "[STEP] Setup bot systemd service..."
  sudo bash scripts/setup_systemd.sh
elif [[ "${MODE}" == "5" ]]; then
  echo "[STEP] Setup dashboard systemd service..."
  sudo DASHBOARD_PORT="${DASHBOARD_PORT}" bash scripts/setup_dashboard_systemd.sh
else
  echo "[STEP] Menjalankan bot foreground..."
  python main.py
  exit 0
fi

print_line
echo " INSTALL SELESAI"
print_line

echo "Bot status:"
sudo systemctl status optimai-monitor --no-pager || true

echo
echo "Dashboard status:"
sudo systemctl status optimai-dashboard --no-pager || true

echo
echo "Dashboard URL: ${DASHBOARD_URL}"
echo "Login dashboard pakai Telegram ID: ${CHAT_ID}"
echo
echo "Cek log bot:"
echo "  sudo journalctl -u optimai-monitor -f"
echo "Cek log dashboard:"
echo "  sudo journalctl -u optimai-dashboard -f"
