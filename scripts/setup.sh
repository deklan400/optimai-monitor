#!/bin/bash

echo "===================================="
echo "🔥 OPTIMAI MONITOR SETUP START 🔥"
echo "===================================="

# =========================
# UPDATE SYSTEM
# =========================
apt update -y && apt upgrade -y

# =========================
# INSTALL DEPENDENCIES
# =========================
apt install -y python3 python3-pip git screen openssh-client

# =========================
# INSTALL PYTHON LIB
# =========================
pip3 install --upgrade pip
pip3 install -r requirements.txt

# =========================
# CREATE DATA FILES
# =========================
mkdir -p data

[ ! -f data/state.json ] && echo "{}" > data/state.json
[ ! -f data/rewards.json ] && echo "{}" > data/rewards.json
[ ! -f data/history.json ] && echo "{}" > data/history.json
[ ! -f data/logs.txt ] && touch data/logs.txt

# =========================
# INPUT TELEGRAM CONFIG
# =========================
echo "===================================="
echo "📲 SETUP TELEGRAM BOT"
echo "===================================="

read -p "Masukkan BOT TOKEN: " BOT_TOKEN
read -p "Masukkan CHAT ID: " CHAT_ID

# simpan ke .env
cat <<EOF > .env
BOT_TOKEN=$BOT_TOKEN
CHAT_ID=$CHAT_ID
EOF

echo "✅ .env berhasil dibuat"

# =========================
# SET PERMISSION
# =========================
chmod +x main.py

echo "===================================="
echo "✅ SETUP SELESAI"
echo "===================================="

# =========================
# PILIH MODE RUN
# =========================
echo ""
echo "Pilih mode run:"
echo "1. Run langsung"
echo "2. Run background (screen)"
read -p "Pilih (1/2): " MODE

if [ "$MODE" == "2" ]; then
    echo "🚀 Running di background..."
    screen -dmS optimai-monitor python3 main.py
    echo "✅ Bot jalan di background (screen)"
    echo "Gunakan: screen -r optimai-monitor"
else
    echo "🚀 Running langsung..."
    python3 main.py
fi
