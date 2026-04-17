#!/usr/bin/env bash

set -euo pipefail

SERVICE_NAME="optimai-monitor"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "[ERROR] Jalankan script ini dengan sudo/root."
  echo "Contoh: sudo bash scripts/setup_systemd.sh"
  exit 1
fi

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Optimai Monitor Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${PROJECT_DIR}/.venv/bin/python ${PROJECT_DIR}/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "[OK] systemd service aktif: ${SERVICE_NAME}"
echo "[INFO] Cek status: sudo systemctl status ${SERVICE_NAME}"
echo "[INFO] Cek log: sudo journalctl -u ${SERVICE_NAME} -f"
