#!/usr/bin/env bash

set -euo pipefail

echo "===================================="
echo " OPTIMAI MONITOR INSTALLER (UBUNTU)"
echo "===================================="

if [[ "${EUID}" -ne 0 ]]; then
  echo "[INFO] Menjalankan apt membutuhkan sudo/root."
  echo "[INFO] Jika gagal permission, jalankan: sudo bash scripts/install.sh"
fi

echo "[STEP] Update package index..."
sudo apt update -y

echo "[STEP] Install dependency sistem..."
sudo apt install -y python3 python3-venv python3-pip openssh-client screen sshpass

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
[[ -f data/history.json ]] || echo "{}" > data/history.json
[[ -f data/vps_list.json ]] || echo "{}" > data/vps_list.json
[[ -f data/logs.txt ]] || touch data/logs.txt

echo "===================================="
echo " SET TELEGRAM CONFIG"
echo "===================================="
read -r -p "Masukkan BOT_TOKEN: " BOT_TOKEN
read -r -p "Masukkan CHAT_ID: " CHAT_ID

cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
CHAT_ID=${CHAT_ID}
EOF

echo "[OK] .env berhasil dibuat."
echo
echo "Pilih mode run:"
echo "1) Run langsung (foreground)"
echo "2) Run background (screen)"
echo "3) Install systemd service (recommended)"
read -r -p "Pilih [1/2/3]: " MODE

if [[ "${MODE}" == "2" ]]; then
  echo "[STEP] Menjalankan di background via screen..."
  screen -dmS optimai-monitor bash -lc "source .venv/bin/activate && python main.py"
  echo "[OK] Bot berjalan di background."
  echo "Cek: screen -ls"
  echo "Attach: screen -r optimai-monitor"
elif [[ "${MODE}" == "3" ]]; then
  echo "[STEP] Setup systemd service..."
  chmod +x scripts/setup_systemd.sh
  sudo bash scripts/setup_systemd.sh
else
  echo "[STEP] Menjalankan bot..."
  python main.py
fi
