#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="optimai-dashboard"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
PORT="${DASHBOARD_PORT:-8080}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Jalankan dengan sudo/root."
  exit 1
fi

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=OptimAI Monitor Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${PROJECT_DIR}/.venv/bin/python -m uvicorn dashboard:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"

echo "Dashboard aktif di port ${PORT}"
echo "Cek: sudo systemctl status ${SERVICE_NAME}"
